from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal, List
from langchain_core.messages import BaseMessage
from uuid import UUID


class ReactionRequest(BaseModel):
    user_id: Optional[int] = Field(None, description="The ID of the user associated with this reaction.")
    message_id: Optional[int] = Field(None, description="The ID of the message to which the reaction is being applied.")
    message_uuid: Optional[UUID] = Field(None, description="The UUID of the message to which the reaction is being applied.")
    reaction: Optional[bool] = Field(None, description="The reaction value (e.g., True for like, False for dislike).")