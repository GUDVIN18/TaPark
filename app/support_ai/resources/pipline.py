import json
import time
import datetime as dt
import asyncio
import traceback
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from .redis_async_client import AsyncRedisClient
from app.usedesc.service import usedesk_service
from app.include.logging_config import logger as log
from app.include.config import config
from app.core.db import db_pool
from .crud import ChatHisoryCrud, UserProfileCrud
from .schemas import (
    UploadSupportAi, 
    SupportAi,
    IntentType,
    CreateFormType,
    QaAnalyzeType,
    UserProfile,
)
from .exceptions import (
    SupportAiErrorConnect,
)
from .graph_func.graph import (
    _current_history,
    search_vector_db,
    llm_response,
    intent_classifier,
    route_intent_classifier,
    dynemic_rag_context,
    call_admin,
    classify_operator_confirmation,
    route_operator_confirmation,
    request_user_email,
    request_user_content,
    send_form_operator,
    cancel_operator_request,
    qa_analyze,
    route_qa_analyze
)


checkpointer = InMemorySaver()

async def geration_pipe(
        data: UploadSupportAi
) -> SupportAi:
    if not config.QWEN_API_KEY:
        raise SupportAiErrorConnect("API key is not set.")

    graph_config = {
        "configurable": {
            "thread_id": f"support:{data.user_id}",
        }
    }

    start_time = time.time()
    graph = StateGraph(SupportAi)

    # node
    graph.add_node("qa_analyze", qa_analyze)
    graph.add_node("_current_history", _current_history)
    graph.add_node("intent_classifier", intent_classifier) # Определяет вопрос по БЗ / Не по БЗ / сразу оператор
    graph.add_node("dynemic_rag_context", dynemic_rag_context) # Формируется промпт с описанием всех полей для RAG поиска
    graph.add_node("search_vector_db", search_vector_db) # поиск в векторной базе данных
    graph.add_node("call_admin", call_admin) # нужна ли помощь админа? (можем ли мы сами ответить на вопрос по Базе Знаний?)
    graph.add_node("llm_response", llm_response)

    graph.add_node("classify_operator_confirmation", classify_operator_confirmation)
    graph.add_node("request_user_email", request_user_email)
    graph.add_node("request_user_content", request_user_content)
    graph.add_node("send_form_operator", send_form_operator)

    graph.add_node("cancel_operator_request", cancel_operator_request)

    # ребра
    # Определяем, вопрос есть в заготовленной базе или идем в ИИ
    graph.add_edge(START, "qa_analyze")
    graph.add_conditional_edges(
        "qa_analyze",
        route_qa_analyze,
        {
            QaAnalyzeType.QA.value: END,
            QaAnalyzeType.AI.value: "_current_history",
        }
    )
    #Ai
    graph.add_edge("_current_history", "intent_classifier")

    graph.add_conditional_edges(
        "intent_classifier",
        route_intent_classifier,
        {
            IntentType.CHAT.value: "llm_response",
            IntentType.KNOWLEDGE.value: "dynemic_rag_context",
            IntentType.OPERATOR.value: "call_admin",
        }
    )
    graph.add_edge("dynemic_rag_context", "search_vector_db")
    graph.add_edge("search_vector_db", "llm_response")
    graph.add_edge("llm_response", END)

    # Ветка оператора
    graph.add_edge("call_admin", "classify_operator_confirmation")
    graph.add_conditional_edges(
        "classify_operator_confirmation",
        route_operator_confirmation,
        {
            CreateFormType.CONFIRMED.value: "request_user_email",
            CreateFormType.DECLINED.value: "cancel_operator_request",
            CreateFormType.NEW_QUESTION.value: "intent_classifier",
        }
    )
    graph.add_edge("request_user_email", "request_user_content")
    graph.add_edge("request_user_content", "send_form_operator")

    graph.add_edge("send_form_operator", END)
    graph.add_edge("cancel_operator_request", END)

    app = graph.compile(checkpointer=checkpointer)

    try:
        snapshot = await app.aget_state(graph_config)
        if snapshot.next:
            result = await app.ainvoke(
                Command(resume=data.message),
                config=graph_config,
            )
        else:
            initial_state = SupportAi(**data.model_dump())
            result = await app.ainvoke(
                initial_state,
                config=graph_config
            )
        interrupts = result.get("__interrupt__", ())

        if interrupts:
            interrupt_data = interrupts[0].value
            snapshot = await app.aget_state(graph_config)

            state_values = dict(snapshot.values)
            state_values["answer"] = interrupt_data["message"]

            result = SupportAi(**state_values)
        else:
            result = SupportAi(**result)

        try:
            async with db_pool.get_connection() as conn:
                user_profile = await UserProfileCrud.get(conn=conn,user_id=data.user_id)
                if not user_profile:
                    user_profile = await UserProfileCrud.create(
                        conn=conn,
                        data=UserProfile(
                            user_id=data.user_id
                        )
                    )
                
                
            async with AsyncRedisClient(
                session_id=str(data.user_id)
            ) as client:
                await client.add_message(
                    role="user",
                    message=data.message,
                )

                await client.add_message(
                    role="ai",
                    message=result.answer,
                    rag_context={
                        "question": data.message,
                        "answer": result.answer,
                        "rag_query": result.rag_query,
                        "rag_context": result.llm_rag_context,
                        "context": result.context_vector_db,
                    } if result.llm_rag_context or result.context_vector_db else None,
                )
        except Exception as e:
            log.error(f"Ошибка в SupportAi при добавлении истории: {e}")
        end_time = time.time()

        log.success(f"{data.user_id}: SupportAi Pipeline execution time: {end_time - start_time:.2f} seconds")
        return result
    except Exception as e:
        raise SupportAiErrorConnect(f"Ошибка в SupportAi Pipeline: {e}\n{traceback.format_exc()}")




if __name__ == "__main__":
    import asyncio
    from app.include.config import config
    from app.support_ai.resources.schemas import UploadSupportAi

    async def main():
        data = UploadSupportAi(
            user_id="1515",
            message="привет"
        )
        print(f"Результат: {await geration_pipe(data)}")

    asyncio.run(main())
