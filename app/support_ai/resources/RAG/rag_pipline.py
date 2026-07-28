from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from typing import Any
from app.include.config import config
from app.include.embeddings.qwen_embedding import QwenEmbedding
from app.include.logging_config import logger as log


embeddings = QwenEmbedding(
    model=config.EMBEDDING_MODEL_ID,
    dimensions=config.VECTOR_DIMENSION
)

SEARCH_KWARGS = {"k": 12, "fetch_k": 35, "lambda_mult": 0.75}


def _vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT),
        collection_name=config.COLLECTION_NAME_AI,
        embedding=embeddings,
        retrieval_mode="dense",
        content_payload_key="full_context",
        metadata_payload_key="payload",
    )


def _rag_scopes(rag_context: dict[str, Any] | None) -> list[tuple[str, list[str]]]:
    chapters = (rag_context or {}).get("chapters") or []
    if not chapters:
        return []

    return [
        (chapter.get("title", ""), chapter.get("children") or [])
        for chapter in chapters
        if chapter.get("title")
    ]


def build_rag_query(message: str, rag_context: dict[str, Any] | None = None) -> str:
    """Собирает более точную строку для embedding-поиска"""
    if not rag_context:
        return message

    scopes = _rag_scopes(rag_context)

    query_parts = [
        message, # Исходный вопрос пользователя сохраняется в RAG-запросе
        rag_context.get("query_focus", ""),
        *[
            f"Раздел: {chapter_title}. Подразделы: {', '.join(child_titles)}"
            if child_titles else f"Раздел: {chapter_title}"
            for chapter_title, child_titles in scopes
        ],
    ]
    return "\n".join(part for part in query_parts if part)


def _metadata_filter(rag_context: dict[str, Any] | None = None) -> models.Filter | None:
    filter_variants = []

    for chapter_title, child_titles in _rag_scopes(rag_context):
        if child_titles:
            for child_title in child_titles:
                for metadata_key in ("subtitle", "topic", "section"):
                    filter_variants.append(
                        models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="chapter",
                                    match=models.MatchValue(value=chapter_title),
                                ),
                                models.FieldCondition(
                                    key=metadata_key,
                                    match=models.MatchValue(value=child_title),
                                ),
                            ]
                        )
                    )
        else:
            filter_variants.append(
                models.Filter(
                    must=[
                        models.FieldCondition(
                            key="chapter",
                            match=models.MatchValue(value=chapter_title),
                        )
                    ]
                )
            )

    if not filter_variants:
        return None

    if len(filter_variants) == 1:
        return filter_variants[0]

    return models.Filter(should=filter_variants)


def _retriever(vector_store: QdrantVectorStore, qdrant_filter: models.Filter | None = None):
    search_kwargs = SEARCH_KWARGS.copy()
    if qdrant_filter:
        search_kwargs["filter"] = qdrant_filter

    return vector_store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )


async def retrieve_docs(query: str, rag_context: dict[str, Any] | None = None):
    vector_store = _vector_store()
    qdrant_filter = _metadata_filter(rag_context)

    try:
        docs = await _retriever(vector_store, qdrant_filter).ainvoke(query)
        if docs or not qdrant_filter:
            return docs

        log.warning("RAG filter returned 0 documents. Fallback to unfiltered search.")
        return await _retriever(vector_store).ainvoke(query)

    except Exception as e:
        log.error(f"Fallback to unfiltered MMR due to: {e}")
        return await _retriever(vector_store).ainvoke(query)


async def retriever_context(rag_context: dict[str, Any] | None = None):
    return _retriever(_vector_store(), _metadata_filter(rag_context))
