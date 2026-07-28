import json
from app.support_ai.resources.redis_async_client import AsyncRedisClient
from langchain_core.prompts import PromptTemplate
from app.include.logging_config import logger as log
from .llm import main_llm, llm_analytics, SYSTEM_INSTRUCTION
from .parcers import (
    parser_main_llm,
    parser_intent_classifier,
    parcer_rag_context,
    parser_form_type
)
from ..RAG.rag_pipline import build_rag_query, retrieve_docs
from ..schemas import (
    SupportAi,
    IntentType,
    CreateFormType,
)
from app.include.decorator import current_time
from langgraph.types import interrupt
from app.usedesc.service import usedesk_service


def _format_rag_context_history(rag_context_history: list[dict] | None) -> str:
    if not rag_context_history:
        return ""
    contexts = []
    for item in rag_context_history[-6:]:
        context = item.get("context")
        if context:
            contexts.append(context)
    return "\n\n".join(contexts)


@current_time
async def _current_history(state: SupportAi) -> SupportAi:
    """Узел для получения истории сообщений"""
    # Соединение само закроется, когда мы выйдем из блока async with
    try:
        async with AsyncRedisClient(session_id=f"{state.user_id}") as client:
            current_history = await client.get_session_history_v2(limit=6)
            rag_context_history = await client.get_recent_rag_contexts(limit=6)
        state.history_messages = current_history
        state.rag_context_history = rag_context_history
        log.debug(f"{state.user_id}: История подгружена. Всего {len(current_history)} сообщений.")
        log.debug(f"{state.user_id}: RAG контекстов подгружено: {len(rag_context_history)}.")
    except Exception as e:
        log.error(f"{state.user_id}: Ошибка при получении истории сообщений: {e}")
    return state

@current_time
async def intent_classifier(state: SupportAi) -> SupportAi:
    """Узел для классификации намерения пользователя"""
    with open("app/support_ai/resources/RAG/knowledge_base/shema.json", "r", encoding="utf-8") as f:
        rag_schema = json.load(f)
    history_messages = state.history_messages[-6:] if state.history_messages else []
    
    prompt_template = PromptTemplate(
        template="""
    Ты классифицируешь текущее сообщение пользователя для выбора маршрута обработки.

    Доступные категории: KNOWLEDGE, CHAT, OPERATOR.

    KNOWLEDGE — вопрос относится к работе, настройкам, функциям или разделам системы TA-PArk и требует поиска информации в базе знаний.

    Выбирай KNOWLEDGE, если пользователь:

    * спрашивает, как выполнить действие в системе;
    * просит инструкцию или объяснение;
    * спрашивает, где находится функция, кнопка или раздел;
    * спрашивает о возможностях, настройках или правилах работы системы;
    * сообщает о проблеме и ожидает инструкцию по её решению;
    * кратко сообщает о сбое или об отсутствии ожидаемого результата в системе,
      даже если не использует вопросительные слова: «не начислилось», «не списалось»,
      «не обновилось», «не загрузилось», «не получилось»;
    * задаёт уточняющий вопрос по теме системы;
    * использует формулировки «как изменить», «как удалить», «как добавить», «как настроить», «как исправить», «где найти».

    Важно:
    * вопрос о том, как пользователь может выполнить действие самостоятельно,
      всегда относится к KNOWLEDGE, если тема присутствует в схеме базы знаний;
    * сообщение о техническом симптоме сначала относится к KNOWLEDGE: нужно
      проверить, есть ли в базе знаний условия, сроки, ограничения или инструкция;
    * пример «Не прошло списание аренды» относится к KNOWLEDGE, а не к OPERATOR.

    OPERATOR — пользователь просит живого специалиста либо просит выполнить действие вместо него.

    Выбирай OPERATOR, если пользователь:

    * явно просит позвать или подключить оператора;
    * просит сотрудника самостоятельно изменить, удалить, добавить или восстановить данные;
    * просит выполнить действие в системе вместо него;
    * сообщает о конфликте, жалобе или спорной ситуации и явно просит решения
      или вмешательства сотрудника;
    * сообщает, что инструкция не помогла и ему требуется помощь специалиста.

    Не выбирай OPERATOR только из-за наличия слов «изменить», «удалить»,
    «увольнение», «исправить», «настроить», «не прошло» или «не списалось».
    Само сообщение о проблеме не является просьбой выполнить действие за
    пользователя. Сначала попробуй найти решение в базе знаний.

    CHAT — сообщение не требует поиска в базе знаний и может быть обработано на основе обычного общения или истории диалога.

    Выбирай CHAT, если пользователь:
    * задаёт уточнение, ответ на которое полностью содержится в истории.

    Приоритет классификации:

    1. Явная просьба подключить оператора — OPERATOR.
    2. Просьба выполнить действие вместо пользователя — OPERATOR.
    3. Сообщение о техническом симптоме в TA-PArk — KNOWLEDGE.
    4. Вопрос о том, как выполнить действие самостоятельно — KNOWLEDGE.
    5. Вопрос относится к разделу или подразделу из схемы базы знаний — KNOWLEDGE.
    6. Для ответа достаточно истории или обычного общения — CHAT.
    7. Если есть сомнение между KNOWLEDGE и OPERATOR — выбирай KNOWLEDGE.
    8. Если есть сомнение между KNOWLEDGE и CHAT — выбирай KNOWLEDGE.

    Схема базы знаний:
    {rag_schema}

    История диалога:
    {history}

    Последние RAG контексты предыдущих ответов:
    {rag_context_history}

    Текущий вопрос пользователя:
    {input}

    {format_instructions}

    Верни ТОЛЬКО JSON без дополнительных комментариев! 
    Значение intent должно быть строго одним из: CHAT, KNOWLEDGE или OPERATOR.
    """,
        input_variables=[
            "input",
            "history",
            "rag_context_history",
            "rag_schema"
        ],
        partial_variables={
            "format_instructions": parser_intent_classifier.get_format_instructions(),
        }
    )

    chain = prompt_template | llm_analytics | parser_intent_classifier
    result = await chain.ainvoke({
        "input": state.message,
        "history": history_messages,
        "rag_context_history": state.rag_context_history or [],
        "rag_schema": rag_schema
    })
    state.intent_classifier = result['intent']
    state.rag_schema = rag_schema
    log.debug(f"\n\n{rag_schema=}\n")
    log.info(f"{state.user_id}: Классификация намерения: {result['intent']}")
    return state

def route_intent_classifier(state: SupportAi) -> str:
    if state.intent_classifier == IntentType.CHAT.value:
        return IntentType.CHAT.value
    if state.intent_classifier == IntentType.KNOWLEDGE.value:
        return IntentType.KNOWLEDGE.value
    if state.intent_classifier == IntentType.OPERATOR.value:
        return IntentType.OPERATOR.value
    return IntentType.OPERATOR.value


@current_time
async def dynemic_rag_context(state: SupportAi) -> SupportAi:
    """Узел для динамического формирования промпта для RAG поиска"""
    prompt_template = PromptTemplate(
        template="""
    Ты должен сформировать краткий контекст для точного поиска в базе знаний.
    У тебя есть схема базы знаний, которая описывает разделы chapters[title] и подразделы chapters[children].

    Правила выбора:
        1. Выбирай минимальный набор разделов для ответа на вопрос пользователя.
        2. Обычно выбирай один основной раздел и один самый релевантный подраздел.
        Добавляй второй раздел только если вопрос действительно объединяет две темы.
        3. Не добавляй родительские или смежные разделы "на всякий случай".
        4. Если вопрос точно совпадает с названием подраздела, верни только этот подраздел внутри его родительского раздела.
        5. Если вопрос является уточнением к предыдущему ответу, используй историю диалога и последние RAG контексты,
        чтобы сохранить прежнюю тему поиска.
        6. Не подменяй тему похожим подразделом. Если общий вопрос относится к
        разделу, но подходящего подраздела в схеме нет, верни родительский раздел
        с пустым списком children. Это означает поиск по всему разделу.
        7. Подраздел "Импорт автомобилей" выбирай только когда пользователь явно
        спрашивает об импорте или интеграции. Для обычного добавления или создания
        автомобиля выбери раздел "Автомобили" с пустым списком children.
        8. Для проблем с начислением или списанием аренды сначала выбирай
        "Водители" → "Начисления". Раздел "Автомобили" → "Условия аренды"
        добавляй только если пользователь спрашивает именно о настройке условий.
        9. query_focus должен сохранять конкретное действие или симптом из
        текущего сообщения, а не заменять его общим названием раздела.

    Дполнения по разделам:
        1. Раздел Печатные формы отвечает в том числе за Договора.

    Схема базы знаний:
    {rag_schema}

    История диалога:
    {history}

    Последние RAG контексты предыдущих ответов:
    {rag_context_history}

    Вопрос пользователя:
    {input}

    {format_instructions}
    Верни ТОЛЬКО JSON без дополнительных комментариев! 
    В значениях title и children используй только названия из схемы базы знаний.
    """,
        input_variables=[
            "input",
            "history",
            "rag_context_history",
            "rag_schema",
        ],
        partial_variables={
            "format_instructions": parcer_rag_context.get_format_instructions(),
        }
    )
    chain = prompt_template | llm_analytics | parcer_rag_context
    result = await chain.ainvoke({
        "input": state.message,
        "history": state.history_messages[-6:] if state.history_messages else [],
        "rag_context_history": state.rag_context_history or [],
        "rag_schema": state.rag_schema
    })
    log.info(f"{state.user_id}: Динамический контекст для RAG поиска сформирован: {result['rag_context']}")
    state.llm_rag_context = result['rag_context']
    return state


@current_time
async def search_vector_db(state: SupportAi) -> SupportAi:
    """Узел для поиска докуметов в векторной БД"""
    rag_query = build_rag_query(state.message, state.llm_rag_context)
    state.rag_query = rag_query
    docs = await retrieve_docs(rag_query, state.llm_rag_context)
    context_text = "\n\n".join([doc.page_content for doc in docs])
    state.context_vector_db = context_text
    log.debug(f"{state.user_id}: Найдено {len(docs)} документов")
    return state


@current_time
async def call_admin(state: SupportAi) -> SupportAi:
    """Запрашивает подтверждение создания заявки"""

    confirmation = interrupt({
        "type": "operator_confirmation",
        "message": (
            "Ваш вопрос требует вмешательства оператора. "
            "Вы готовы заполнить форму обратной связи?"
        ),
    })
    state.message = str(confirmation).strip()

    log.info(
        f"{state.user_id}: Получен ответ на создание заявки: "
        f"{state.message}"
    )
    return state


@current_time
async def classify_operator_confirmation(state: SupportAi) -> SupportAi:
    """Узел для определения намеренья создания заявки"""
    history_messages = state.history_messages[-3:] if state.history_messages else []

    prompt_template = PromptTemplate(
        template="""
    Ты классифицируешь текущее сообщение пользователя для определения - создаем зявку или нет.

    Доступные категории: CONFIRMED, DECLINED

    CONFIRMED - если пользователь подтверждает создание заявки
    DECLINED - если пользователь отказывается от создания заявки

    История диалога:
    {history}

    Текущий вопрос пользователя:
    {input}

    {format_instructions}

    Верни ТОЛЬКО JSON без дополнительных комментариев!
    Значение form_type должно быть строго одним из: CONFIRMED, DECLINED
    """,
        input_variables=[
            "input",
            "history",
        ],
        partial_variables={
            "format_instructions": parser_form_type.get_format_instructions(),
        }
    )

    chain = prompt_template | llm_analytics | parser_form_type
    result = await chain.ainvoke({
        "input": state.message,
        "history": history_messages,
    })
    state.create_form = result['form_type']
    log.info(f"{state.user_id}: Классификация составления заявки: {result['form_type']}")
    return state


def route_operator_confirmation(state: SupportAi) -> str:
    """Направляет диалог по сохраненному результату классификации."""
    if isinstance(state.create_form, CreateFormType):
        return state.create_form.value
    return str(state.create_form)


@current_time
async def request_user_email(state: SupportAi) -> SupportAi:
    """Запрашивает email пользователя для обратной связи"""

    email = interrupt({
        "type": "user_email",
        "message": (
            "Укажите, пожалуйста, ваш email для обратной связи."
        ),
    })

    state.user_email = str(email).strip()
    state.message = state.user_email

    log.info(
        f"{state.user_id}: Получен email для заявки: "
        f"{state.user_email}"
    )

    return state


@current_time
async def request_user_content(state: SupportAi) -> SupportAi:
    """Запрашивает содержание обращения пользователя"""

    user_content = interrupt({
        "type": "user_content",
        "message": (
            "Опишите, пожалуйста, что вы хотите узнать "
            "или какую проблему необходимо решить."
        ),
    })

    state.user_content = str(user_content).strip()
    state.message = state.user_content

    log.info(
        f"{state.user_id}: Получено содержание заявки: "
        f"{state.user_content}"
    )

    return state

@current_time
async def send_form_operator(state: SupportAi) -> SupportAi:
    text = (
        "Новая заявка в тех. поддержку через AI\n\n"
        f"Email: {state.user_email}\n"
        f"Сообщение пользователя: {state.user_content}"
    )
    await usedesk_service.send_message(
        text=text,
        sender='client',
        name=f"Клиент {state.user_email}",
        email=state.user_email
    )
    state.answer = "Ваша заявка успешно отправлена!"
    return state


@current_time
async def cancel_operator_request(state: SupportAi) -> SupportAi:
    """Пользователь отказался от создания заявки"""
    log.info(
        f"{state.user_id}: Пользователь отказался от создания заявки."
    )
    state.answer = (
        "Хорошо, заявка не будет создана. "
        "Если у вас возникнут другие вопросы, я постараюсь помочь."
    )
    return state


@current_time
async def llm_response(state: SupportAi) -> SupportAi:
    """Узел для ответа пользователю на вопрос по контексту из базы знаний"""
    previous_context = _format_rag_context_history(state.rag_context_history)
    context_parts = []

    if state.context_vector_db:
        context_parts.append(f"Текущий найденный контекст:\n{state.context_vector_db}")

    if previous_context:
        context_parts.append(f"Контекст предыдущих ответов:\n{previous_context}")

    context = "\n\n".join(context_parts) if context_parts else "Нет контекста из базы знаний."

    prompt_template = PromptTemplate(
        template="""
    {system_instructions}

    Контекст из базы знаний:
    {context}

    Правило использования контекста:
    Если контекст содержит описание назначения раздела, список функций или доступных операций,
    этого достаточно для ответа. Не пиши, что в базе знаний нет определения.

    История диалога:
    {history}

    Вопрос пользователя:
    {question}

    {format_instructions}

    Верни ТОЛЬКО JSON без дополнительных комментариев! 
    не допускай использование английскийх слов в ответе
    """,
        input_variables=[
            "context",
            "history",
            "question",
        ],
        partial_variables={
            "format_instructions": parser_main_llm.get_format_instructions(),
            "system_instructions": SYSTEM_INSTRUCTION
        }
    )

    chain = prompt_template | main_llm | parser_main_llm
    try:
        response = await chain.ainvoke({
            "context": context,
            "history": state.history_messages,
            "question": state.message
        })
        state.answer = response['answer']
        log.success(f"\n\n{state.user_id}: Ответ сформирован: {state.answer}")
    except Exception as e:
        log.error(f"{state.user_id}: Ошибка в llm_response: {e}")
    return state
