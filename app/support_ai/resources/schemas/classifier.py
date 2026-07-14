from pydantic import BaseModel, Field
from typing import List
from .type_ansers import IntentType


class IntentClassifier(BaseModel):
    intent: IntentType = Field(
        description="Результат классификации намерения пользователя"
    )


class RagContextChapter(BaseModel):
    title: str = Field(
        description="Название основного раздела базы знаний"
    )
    children: List[str] = Field(
        default_factory=list,
        description="Только самые релевантные подразделы выбранного раздела"
    )


class RagContext(BaseModel):
    chapters: List[RagContextChapter] = Field(
        description="Минимальный список разделов для точного RAG поиска"
    )
    query_focus: str = Field(
        description="Краткая формулировка темы поиска на русском языке"
    )


class DynemicRagContext(BaseModel):
    rag_context: RagContext = Field(
        description="Динамически сформированный контекст для RAG поиска"
    )
    
