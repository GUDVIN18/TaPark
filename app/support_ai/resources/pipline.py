import json
import time
import asyncio
import traceback
from langgraph.graph import StateGraph, START, END
from .redis_async_client import AsyncRedisClient
from app.include.logging_config import logger as log
from app.include.config import config
from .schemas import (
    UploadSupportAi, 
    SupportAi,
    IntentType,

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
    call_admin
)


async def geration_pipe(
        data: UploadSupportAi
) -> SupportAi:
    if not config.QWEN_API_KEY:
        raise SupportAiErrorConnect("API key is not set.")
    start_time = time.time()
    graph = StateGraph(SupportAi)

    # node
    graph.add_node("_current_history", _current_history)
    graph.add_node("intent_classifier", intent_classifier) # Определяет вопрос по БЗ / Не по БЗ / сразу оператор
    graph.add_node("dynemic_rag_context", dynemic_rag_context) # Формируется промпт с описанием всех полей для RAG поиска
    graph.add_node("search_vector_db", search_vector_db) # поиск в векторной базе данных
    graph.add_node("call_admin", call_admin) # нужна ли помощь админа? (можем ли мы сами ответить на вопрос по Базе Знаний?)
    graph.add_node("llm_response", llm_response)

    # ребра
    graph.add_edge(START, "_current_history")
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

    # graph.add_conditional_edges(
    #     "_help_admin",
    #     route_advice,
    #     # {
    #     #     AdviceType.ANALYSIS_ADVICE.value: "llm_response",
    #     #     AdviceType.GENERATION_ADVICE.value: "call_admin",
    #     # }
    #     {
    #     }
    # )

    graph.add_edge("llm_response", END)
    graph.add_edge("call_admin", END)
    app = graph.compile()

    try:
        initial_state = SupportAi(**data.model_dump())

        result = await app.ainvoke(initial_state)
        if result:
            try:
                async with AsyncRedisClient(session_id=f"{data.user_id}") as client:
                    await client.add_message(
                        role="user",
                        message=result['message']
                    )
                    await client.add_message(
                        role="ai",
                        message=result['answer'],
                        rag_context={
                            "question": result.get("message"),
                            "answer": result.get("answer"),
                            "rag_query": result.get("rag_query"),
                            "rag_context": result.get("llm_rag_context"),
                            "context": result.get("context_vector_db"),
                        } if result.get("llm_rag_context") or result.get("context_vector_db") else None
                    )
            except Exception as e:
                log.error(f"Ошибка в SupportAi при добавлении истории: {e}")
            end_time = time.time()
            log.success(f"{data.user_id}: SupportAi Pipeline execution time: {end_time - start_time:.2f} seconds")
            return SupportAi(**result)
    except Exception as e:
        raise SupportAiErrorConnect(f"Ошибка в SupportAi Pipeline: {e}\n{traceback.format_exc()}")




if __name__ == "__main__":
    import asyncio
    from app.include.config import config
    from app.support_ai.resources.schemas import UploadSupportAi

    async def main():
        data = UploadSupportAi(
            user_id="1",
            message="а какие важные детали при расчете?"
        )
        await geration_pipe(data)

    asyncio.run(main())


