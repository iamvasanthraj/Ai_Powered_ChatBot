from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Chat(BaseModel):
    chat_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_temporary: bool = False

class Message(BaseModel):
    chat_id: str
    role: Literal['user', 'assistant']
    content: str
    timestamp: datetime
