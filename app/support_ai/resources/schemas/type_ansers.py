from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal, List
from langchain_core.messages import BaseMessage
from enum import Enum


class IntentType(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    OPERATOR = "OPERATOR"
    CHAT = "CHAT"

class CreateFormType(str, Enum):
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    NEW_QUESTION = "NEW_QUESTION"
