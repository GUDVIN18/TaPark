from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal, List
from langchain_core.messages import BaseMessage
from enum import Enum


class ChatHistory(BaseModel):
    user_id: Optional[int] = Field(None, description="The ID of the user associated with this chat history.")
    role: Optional[str] = Field(None, description="The role of the message sender (e.g., 'user', 'assistant').")
    content: Optional[str] = Field(None, description="The content of the chat message.")
    reactions: Optional[bool] = Field(None, description="Reactions to the chat message.")
    created_at: Optional[str] = Field(None, description="The timestamp when the chat history was created.")

class ChatHistoryFrom(ChatHistory):
    id: Optional[int] = Field(None, description="The unique identifier of the chat history entry.")
    uuid: Optional[str] = Field(None, description="The UUID of the chat history entry.")
    updated_at: Optional[str] = Field(None, description="The timestamp when the chat history entry was last updated.")