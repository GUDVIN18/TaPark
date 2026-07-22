from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal, List
from langchain_core.messages import BaseMessage
from .buttons import Button, ButtonType
from .type_ansers import CreateFormType


class UploadSupportAi(BaseModel):
    message: str = Field(
        description="Вопрос пользователя"
    )
    user_id: int = Field(
        description="Уникальный идентификатор пользователя"
    )


class SupportAi(UploadSupportAi):
    history_messages: List[BaseMessage] = Field(
        None,
        description="История сообщений пользователя"
    )
    rag_context_history: List[Dict[str, Any]] = Field(
        None,
        description="Последние RAG контексты, сохраненные вместе с ответами"
    )
    rag_schema: Dict[str, Any] = Field(
        None,
        description="Схема для RAG поиска в векторной базе знаний"
    )
    intent_classifier: str = Field(
        None,
        description="Результат классификации намерения пользователя: KNOWLEDGE / OPERATOR"
    )
    llm_rag_context: Dict[str, Any] = Field(
        None,
        description="Контекст для RAG поиска в векторной базе знаний"
    )
    rag_query: str = Field(
        None,
        description="Строка поискового запроса для RAG"
    )
    context_vector_db: str = Field(
        None,
        description="Контекст из векторной базы знаний для формирования ответа"
    )
    create_form: Optional[CreateFormType] = Field(
        None,
        description="Создание заявки в тех поддержку"
    )
    user_email: str = Field(
        None,
        description="Email пользователя"
    )
    user_content: str = Field(
        None,
        description="Вопрос пользователя в поддержку"
    )
    answer: str = Field(
        None,
        description=(
            "Ответ пользователю."
        )
    )

    # buttons: Optional[List[Button]] = Field(
    #     default=None,
    #     description=f"""
    # Кнопки для UI. Генерируй ТОЛЬКО при необходимости на основе текущего answer и context_vector_db.

    # ПРАВИЛА:
    # 1. {ButtonType.ADD_HABIT.value} (1-3 шт): конкретные действия/предметы из answer
    # - Извлекай из текста ответа, не придумывай
    # - Формат: краткое существительное/действие, 1-3 слова
    # - Пример логики: если в answer упомянуты "шторы блэкаут" и "маска" → label = "Шторы блэкаут", "Маска для сна"
    # - Генерируй кнопки только для НОВЫХ ритуалов/действий, которые предложены в текущем ответе на текущий вопрос пользователя
    # - Если такой же ритуал/действие уже предлагалось в предыдущем ответе ассистента или уже было кнопкой в предыдущем ответе, НЕ повторяй эту кнопку

    # ЗАПРЕЩЕНО:
    # - Копировать кнопки из примеров обучения
    # - Генерировать кнопки не связанные с текущим answer
    # - Генерировать если ответ — уточняющий вопрос
    # - Генерировать при благодарности, прощании, подтверждении или завершении диалога: "спасибо", "благодарю", "понял", "ок", "хорошо", "до свидания", "пока" и похожих сообщениях
    # """)
    
    # 2. add_to_diary (всегда 1 шт): общая тема текущего совета
    # - Формат: "Добавить [тема] в дневник"
    # - Тему бери из сути вопроса пользователя, не из примеров

class UpdateKbRequest(BaseModel):
    path: str = Field(description="Относительный путь до загруженного .md файла")
