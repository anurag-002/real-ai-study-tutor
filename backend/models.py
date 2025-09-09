from typing import Optional, List, Literal
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    session_id: Optional[str] = None
    input_type: Literal["text", "voice"] = "text"
    content: str


class SendMessageResponse(BaseModel):
    session_id: str
    reply_text: str
    reply_audio_url: Optional[str]
    timestamp: str


class UploadFileResponse(BaseModel):
    session_id: str
    reply_text: str
    reply_audio_url: Optional[str]
    timestamp: str


class ChatMessage(BaseModel):
    sender: Literal["user", "ai"]
    content: str
    audio_url: Optional[str] = None
    timestamp: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]


class ResetHistoryRequest(BaseModel):
    session_id: str


