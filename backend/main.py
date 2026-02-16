from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_db
from mcp_server import orchestrate_llm
from utils import generate_title

logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


CHATS: Dict[str, Dict[str, Any]] = {}
MESSAGES: Dict[str, List[Dict[str, Any]]] = {}


@app.get("/")
def read_root():
    return {"status": "ok", "message": "MCP Chatbot API is running"}


@app.get("/health")
async def health():
    try:
        await get_db().command("ping")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


class NewChatRequest(BaseModel):
    is_temporary: bool = False
    first_message: str


class MessageRequest(BaseModel):
    content: str
    role: str  # 'user' only from frontend


class LegacyChatRequest(BaseModel):
    message: str


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _require_chat(chat_id: str) -> Dict[str, Any]:
    chat = CHATS.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def _append_message(chat_id: str, role: str, content: str) -> None:
    MESSAGES.setdefault(chat_id, []).append(
        {
            "role": role,
            "content": content,
            "timestamp": _now_iso(),
        }
    )


@app.post("/chat")
async def legacy_chat(req: LegacyChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        response = await orchestrate_llm(req.message, [])
    except Exception:
        response = "I couldn't generate a response right now. Please try again."
    return {"response": response}


@app.post("/chat/new")
async def create_chat(req: NewChatRequest):
    if req.is_temporary:
        chat_id = str(uuid4())
        CHATS[chat_id] = {
            "chat_id": chat_id,
            "title": generate_title(req.first_message) if req.first_message else "Temporary Chat",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "is_temporary": True,
        }
        MESSAGES[chat_id] = []
        return {"chat_id": chat_id, "is_temporary": True}

    chat_id = str(uuid4())
    CHATS[chat_id] = {
        "chat_id": chat_id,
        "title": generate_title(req.first_message) if req.first_message else "New chat",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "is_temporary": False,
    }
    MESSAGES[chat_id] = []
    _append_message(chat_id, "user", req.first_message)

    try:
        response = await orchestrate_llm(req.first_message, MESSAGES.get(chat_id, []))
    except Exception:
        response = "I couldn't generate a response right now. Please try again."

    _append_message(chat_id, "assistant", response)
    CHATS[chat_id]["updated_at"] = _now_iso()
    return {"chat_id": chat_id, "is_temporary": False, "response": response}


@app.get("/chat/list")
async def list_chats():
    chats = list(CHATS.values())
    chats.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    return chats[:100]


@app.get("/chat/{chat_id}")
async def get_chat(chat_id: str):
    chat = _require_chat(chat_id)
    return {"chat": chat, "messages": MESSAGES.get(chat_id, [])[:200]}


@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    _require_chat(chat_id)
    CHATS.pop(chat_id, None)
    MESSAGES.pop(chat_id, None)
    return {"deleted": True, "chat_id": chat_id}


@app.post("/chat/temp/message")
async def post_temp_message(request: Request):
    data = await request.json()
    chat_id = data.get("chat_id")
    content = data.get("content")

    if not chat_id or not content:
        raise HTTPException(400, "chat_id and content are required")

    chat = _require_chat(chat_id)
    if not chat.get("is_temporary"):
        raise HTTPException(status_code=400, detail="Not a temporary chat")

    _append_message(chat_id, "user", content)
    try:
        response = await orchestrate_llm(content, MESSAGES.get(chat_id, []))
    except Exception:
        response = "I couldn't generate a response right now. Please try again."
    _append_message(chat_id, "assistant", response)
    chat["updated_at"] = _now_iso()
    return {"response": response}


@app.post("/chat/{chat_id}/message")
async def post_message(chat_id: str, req: MessageRequest):
    chat = _require_chat(chat_id)
    if chat.get("is_temporary"):
        raise HTTPException(status_code=400, detail="Not a persistent chat")

    _append_message(chat_id, "user", req.content)
    try:
        response = await orchestrate_llm(req.content, MESSAGES.get(chat_id, []))
    except Exception:
        response = "I couldn't generate a response right now. Please try again."
    _append_message(chat_id, "assistant", response)
    chat["updated_at"] = _now_iso()
    return {"response": response}
