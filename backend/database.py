from __future__ import annotations

import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bson import Decimal128, ObjectId

from db import DB_NAME, get_db

MAX_DOCS = 200
DEFAULT_SCAN_LIMIT = 500
DEFAULT_SEARCH_RESULTS = 30


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def dumps_json(value: Any) -> str:
    return json.dumps(_to_jsonable(value), ensure_ascii=False, default=str)


async def list_collections() -> List[Dict[str, Any]]:
    db = get_db()
    names = await db.list_collection_names()
    collections: List[Dict[str, Any]] = []
    for name in sorted(names):
        try:
            count = await db[name].estimated_document_count()
        except Exception:
            count = None
        collections.append({"name": name, "estimated_document_count": count})
    return collections


async def _ensure_collection_exists(collection: str) -> None:
    db = get_db()
    names = await db.list_collection_names()
    if collection not in names:
        if not names:
            raise ValueError(
                f"Collection '{collection}' not found in {DB_NAME}. "
                "No collections were found in this database."
            )
        available = ", ".join(sorted(names))
        raise ValueError(
            f"Collection '{collection}' not found in {DB_NAME}. "
            f"Available collections: {available}"
        )


def _normalize_sort(sort: Any) -> Optional[List[Tuple[str, int]]]:
    if sort is None:
        return None
    if isinstance(sort, list):
        out: List[Tuple[str, int]] = []
        for item in sort:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], str)
                and isinstance(item[1], int)
            ):
                out.append((item[0], item[1]))
        return out or None
    if isinstance(sort, dict):
        out2: List[Tuple[str, int]] = []
        for k, v in sort.items():
            if isinstance(k, str) and isinstance(v, int):
                out2.append((k, v))
        return out2 or None
    return None


def _clamp_limit(limit: Any, default: int = 50) -> int:
    try:
        value = int(limit)
    except Exception:
        value = default
    return max(1, min(MAX_DOCS, value))


def _reject_unsupported_operators(payload: Any) -> None:
    """
    Basic safety: disallow server-side JS and other risky operators.
    """
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(k, str) and k in {"$where", "$function", "$accumulator"}:
                raise ValueError(f"Unsupported operator: {k}")
            _reject_unsupported_operators(v)
    elif isinstance(payload, list):
        for item in payload:
            _reject_unsupported_operators(item)


async def find_documents(
    *,
    collection: str,
    filter: Optional[Dict[str, Any]] = None,
    projection: Optional[Dict[str, Any]] = None,
    sort: Any = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    await _ensure_collection_exists(collection)
    _reject_unsupported_operators(filter or {})
    _reject_unsupported_operators(projection or {})

    db = get_db()
    cursor = db[collection].find(filter or {}, projection)
    sort_spec = _normalize_sort(sort)
    if sort_spec:
        cursor = cursor.sort(sort_spec)
    docs = await cursor.limit(_clamp_limit(limit)).to_list(length=_clamp_limit(limit))
    return _to_jsonable(docs)


async def aggregate_documents(
    *,
    collection: str,
    pipeline: List[Dict[str, Any]],
    limit: int = 200,
) -> List[Dict[str, Any]]:
    await _ensure_collection_exists(collection)
    if not isinstance(pipeline, list) or not all(isinstance(s, dict) for s in pipeline):
        raise ValueError("pipeline must be a list of stage objects")
    _reject_unsupported_operators(pipeline)

    db = get_db()
    cursor = db[collection].aggregate(pipeline, allowDiskUse=False)
    docs = await cursor.to_list(length=_clamp_limit(limit, default=MAX_DOCS))
    return _to_jsonable(docs)


async def count_documents(
    *,
    collection: str,
    filter: Optional[Dict[str, Any]] = None,
) -> int:
    await _ensure_collection_exists(collection)
    _reject_unsupported_operators(filter or {})
    db = get_db()
    return int(await db[collection].count_documents(filter or {}))


async def find_one_document(
    *,
    collection: str,
    filter: Optional[Dict[str, Any]] = None,
    projection: Optional[Dict[str, Any]] = None,
    sort: Any = None,
) -> Optional[Dict[str, Any]]:
    docs = await find_documents(
        collection=collection,
        filter=filter,
        projection=projection,
        sort=sort,
        limit=1,
    )
    if not docs:
        return None
    return docs[0]


def _tokenize_query(query: str) -> List[str]:
    raw = (query or "").lower()
    tokens: List[str] = []
    current: List[str] = []
    for ch in raw:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))

    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "them",
        "his",
        "her",
        "their",
        "my",
        "your",
        "our",
        "as",
        "at",
        "by",
        "from",
        "not",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
    }
    uniq: List[str] = []
    seen = set()
    for t in tokens:
        if len(t) < 3 or t in stop:
            continue
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
    return uniq[:12]


def _score_doc(doc: Any, tokens: List[str], query: str) -> int:
    try:
        text = dumps_json(doc).lower()
    except Exception:
        text = str(doc).lower()

    if not text:
        return 0

    score = 0
    for t in tokens:
        if t in text:
            score += 3
    q = (query or "").strip().lower()
    if q and q in text:
        score += 10
    return score


async def search_documents_text(
    *,
    collection: str,
    query: str,
    projection: Optional[Dict[str, Any]] = None,
    scan_limit: int = DEFAULT_SCAN_LIMIT,
    return_limit: int = DEFAULT_SEARCH_RESULTS,
) -> List[Dict[str, Any]]:
    """
    Best-effort search when schema is unknown.

    - Tries MongoDB $text if an index exists, otherwise falls back to client-side scoring.
    - Returns up to return_limit documents.
    """
    await _ensure_collection_exists(collection)
    db = get_db()
    _reject_unsupported_operators(projection or {})

    limit = max(1, min(MAX_DOCS, int(return_limit) if return_limit else DEFAULT_SEARCH_RESULTS))

    # Attempt full-text search if possible.
    try:
        proj = dict(projection or {})
        proj["score"] = {"$meta": "textScore"}
        cursor = (
            db[collection]
            .find({"$text": {"$search": query or ""}}, proj)
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        for d in docs:
            if isinstance(d, dict):
                d.pop("score", None)
        return _to_jsonable(docs)
    except Exception:
        pass

    # Fallback: scan a limited number of docs and score client-side.
    scan = max(1, int(scan_limit) if scan_limit else DEFAULT_SCAN_LIMIT)
    scan = min(5000, scan)
    cursor2 = db[collection].find({}, projection).limit(scan)
    docs2 = await cursor2.to_list(length=scan)

    tokens = _tokenize_query(query)
    scored: List[Tuple[int, Any]] = []
    for d in docs2:
        s = _score_doc(d, tokens, query)
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [d for _, d in scored[:limit]]
    return _to_jsonable(top)
