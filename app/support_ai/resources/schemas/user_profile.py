import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal, List
from langchain_core.messages import BaseMessage
from enum import Enum
from uuid import UUID


class UserProfile(BaseModel):
    user_id: int = Field(..., description="The ID of the user associated with this profile.")
    created_at: Optional[datetime.datetime] = Field(None, description="The timestamp when the user profile was created.")

class UserProfileFrom(UserProfile):
    id: Optional[int] = Field(None, description="The unique identifier of the chat history entry.")
    uuid: Optional[UUID] = Field(None, description="The UUID of the chat history entry.")
    updated_at: Optional[datetime.datetime] = Field(None, description="The timestamp when the chat history entry was last updated.")