import asyncio
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

SEARCH_KWARGS = {"k": 8, "fetch_k": 30, "lambda_mult": 0.75}
MAX_CONTEXT_DOCUMENTS = 12


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


def _chapter_filter(rag_context: dict[str, Any] | None = None) -> models.Filter | None:
    """Build a less restrictive filter for documents nested under another child.

    The schema shown to the selector is intentionally flat, while Qdrant metadata
    is hierarchical. A selected child can therefore be a sibling of the chunk
    that actually contains the answer. Searching the whole selected chapter in
    parallel prevents that answer from being filtered out.
    """
    chapters = [
        models.FieldCondition(
            key="chapter",
            match=models.MatchValue(value=chapter_title),
        )
        for chapter_title, _ in _rag_scopes(rag_context)
    ]
    if not chapters:
        return None
    if len(chapters) == 1:
        return models.Filter(must=[chapters[0]])
    return models.Filter(should=[
        models.Filter(must=[chapter_condition])
        for chapter_condition in chapters
    ])


def _retriever(vector_store: QdrantVectorStore, qdrant_filter: models.Filter | None = None):
    search_kwargs = SEARCH_KWARGS.copy()
    if qdrant_filter:
        search_kwargs["filter"] = qdrant_filter

    return vector_store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )


def _merge_document_lists(
    document_lists: list[list[Any]],
    limit: int = MAX_CONTEXT_DOCUMENTS,
) -> list[Any]:
    """Round-robin scoped and global results, removing identical chunks."""
    merged = []
    seen = set()
    max_length = max((len(documents) for documents in document_lists), default=0)

    for index in range(max_length):
        for documents in document_lists:
            if index >= len(documents):
                continue
            document = documents[index]
            identity = document.page_content.strip()
            if not identity or identity in seen:
                continue
            seen.add(identity)
            merged.append(document)
            if len(merged) >= limit:
                return merged

    return merged


async def retrieve_docs(query: str, rag_context: dict[str, Any] | None = None):
    vector_store = _vector_store()
    exact_filter = _metadata_filter(rag_context)
    chapter_filter = _chapter_filter(rag_context)

    # Always include a global search. Previously it ran only when a metadata
    # filter returned zero documents. A non-empty but irrelevant filtered result
    # therefore hid exact FAQ answers stored under another chapter.
    filters = []
    serialized_filters = set()
    for qdrant_filter in (exact_filter, chapter_filter, None):
        identity = (
            qdrant_filter.model_dump_json(exclude_none=True)
            if qdrant_filter is not None
            else "<global>"
        )
        if identity in serialized_filters:
            continue
        serialized_filters.add(identity)
        filters.append(qdrant_filter)

    # Generate the query embedding once. Invoking three retrievers separately
    # would make three identical external embedding requests.
    try:
        query_embedding = await embeddings.aembed_query(query)
    except Exception as error:
        log.error(f"RAG query embedding failed: {error}")
        return []

    results = await asyncio.gather(
        *[
            vector_store.amax_marginal_relevance_search_by_vector(
                query_embedding,
                **SEARCH_KWARGS,
                filter=qdrant_filter,
            )
            for qdrant_filter in filters
        ],
        return_exceptions=True,
    )

    successful_results = []
    for qdrant_filter, result in zip(filters, results):
        if isinstance(result, Exception):
            scope = "global" if qdrant_filter is None else "filtered"
            log.error(f"RAG {scope} search failed: {result}")
            continue
        successful_results.append(result)

    documents = _merge_document_lists(successful_results)
    if not documents:
        log.warning("RAG search returned no documents.")
    return documents


async def retriever_context(rag_context: dict[str, Any] | None = None):
    return _retriever(_vector_store(), _metadata_filter(rag_context))
