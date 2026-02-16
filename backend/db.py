import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).resolve().parent / ".env")

MONGO_HOST = os.getenv("MONGO_HOST", "127.0.0.1")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27019"))
MONGO_URL = os.getenv("MONGO_URL", f"mongodb://{MONGO_HOST}:{MONGO_PORT}/?directConnection=true")

DB_NAME = os.getenv("MONGO_DB_NAME", "mydb")
KNOWLEDGE_COLLECTION = os.getenv("KNOWLEDGE_COLLECTION", "mycollection")
KNOWLEDGE_COLLECTION_ALIASES: List[str] = list(
    dict.fromkeys([KNOWLEDGE_COLLECTION, "mycollection", "products", "orders", "ordes"])
)

client = None
_knowledge_collection_cache: Optional[str] = None

def get_client():
    global client
    if client is None:
        client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
    return client

def get_db():
    return get_client()[DB_NAME]


async def resolve_knowledge_collection() -> str:
    """
    Returns the best matching knowledge collection name in the current DB.
    Falls back to configured aliases if collection discovery is unavailable.
    """
    global _knowledge_collection_cache
    if _knowledge_collection_cache:
        return _knowledge_collection_cache

    db = get_db()
    try:
        existing = await db.list_collection_names()
    except Exception:
        _knowledge_collection_cache = KNOWLEDGE_COLLECTION
        return _knowledge_collection_cache

    existing_lower = {name.lower(): name for name in existing}
    for alias in KNOWLEDGE_COLLECTION_ALIASES:
        match = existing_lower.get(alias.lower())
        if match:
            _knowledge_collection_cache = match
            return _knowledge_collection_cache

    if existing:
        _knowledge_collection_cache = sorted(existing)[0]
        return _knowledge_collection_cache

    _knowledge_collection_cache = KNOWLEDGE_COLLECTION
    return _knowledge_collection_cache


async def create_indexes():
    return
