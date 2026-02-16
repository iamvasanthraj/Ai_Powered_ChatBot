from typing import Dict, List
from models import Message, Chat
from uuid import uuid4
from datetime import datetime

temp_chats: Dict[str, Chat] = {}
temp_messages: Dict[str, List[Message]] = {}

def new_temp_chat() -> str:
    chat_id = str(uuid4())
    chat = Chat(
        chat_id=chat_id,
        title="Temporary Chat",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_temporary=True
    )
    temp_chats[chat_id] = chat
    temp_messages[chat_id] = []
    return chat_id

def add_temp_message(chat_id: str, message: Message):
    if chat_id in temp_messages:
        temp_messages[chat_id].append(message)

def get_temp_messages(chat_id: str) -> List[Message]:
    return temp_messages.get(chat_id, [])

def delete_temp_chat(chat_id: str):
    temp_chats.pop(chat_id, None)
    temp_messages.pop(chat_id, None)
