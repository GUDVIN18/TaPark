from pathlib import Path
from app.include.logging_config import logger as log
from qdrant_client import QdrantClient, models
from tqdm import tqdm
from app.include.config import config
from app.include.embeddings.qwen_embedding import QwenEmbedding
import uuid
import re
import json
from typing import Any
from qdrant_client.models import Distance, VectorParams
from langchain_text_splitters import MarkdownHeaderTextSplitter


# запуск скрипта строго локально. python -m app.support_ai.resources.RAG.qdrant_loader
embeddings_qwen = QwenEmbedding(
    model=config.EMBEDDING_MODEL_ID,
    dimensions=config.VECTOR_DIMENSION
)

qdrant_client = QdrantClient(host="localhost", port=config.QDRANT_PORT)

class SleepAiRagEmbeddingConfig:
    headers_to_split_on = [
        ("#", "chapter"),
        ("##", "subchapter"),
        ("###", "topic"),
        ("####", "section"),
    ]
    header_order = ("chapter", "subchapter", "topic", "section")

    @staticmethod
    def run_qdrant_pipeline(file_path: Path):
        # Пересоздаем коллекцию для чистоты теста
        if qdrant_client.collection_exists(collection_name=f"{config.COLLECTION_NAME_AI}"):
            qdrant_client.delete_collection(collection_name=f"{config.COLLECTION_NAME_AI}")
            
        log.info(f"Создание коллекции: {f'{config.COLLECTION_NAME_AI}'}")
        qdrant_client.recreate_collection(
            collection_name=f"{config.COLLECTION_NAME_AI}",
            vectors_config=VectorParams(size=config.VECTOR_DIMENSION, distance=Distance.COSINE)
        )
        try:
            log.info(f"{qdrant_client.get_collections()}")
        except Exception as e:
            log.error(f"Failed to connect to Qdrant: {e}")
            return

        log.info(f"\n📘 Обработка файла: {file_path.name}")
        clering_file_text = SleepAiRagEmbeddingConfig.clear(file_path)
        schema = SleepAiRagEmbeddingConfig.build_schema(clering_file_text)
        SleepAiRagEmbeddingConfig.write_schema(file_path, schema)
        # структурируем текст на главы, подглавы и т.д.
        structured_text = SleepAiRagEmbeddingConfig.structure_text(clering_file_text, schema=schema)
        # подготовка текста для эмбеддинга
        try:
            preparation = SleepAiRagEmbeddingConfig.preparation(structured_text)

            # Готовим тексты для эмбеддинга
            batch_texts = [d['vector_text'] for d in preparation]
            
            # Получаем вектора
            try:
                vectors = SleepAiRagEmbeddingConfig.get_batch_embeddings(batch_texts)
            except Exception as e:
                log.error(f"Critical Error during embedding: {e}")
                return

            points = []
            for i, doc in enumerate(preparation):
                if i >= len(vectors): 
                    break
                    
                points.append(
                    models.PointStruct(
                        id=str(uuid.uuid4()), # Генерируем уникальный ID
                        vector=vectors[i],
                        payload={
                            "original_file": file_path.name,
                            "chapter": doc['payload'].get('chapter', 'Общее'),
                            "subtitle": doc['payload'].get('subchapter', 'Нет подглавы'),
                            "topic": doc['payload'].get('topic', 'Нет темы'),
                            "section": doc['payload'].get('section', 'Нет секции'),
                            "content": doc['payload'].get('content', 'Пустой текст'),
                            "full_context": doc['vector_text']
                        }
                    )
                )
            
            log.info(f"Загрузка {len(points)} точек в Qdrant...")
            for batch_start in tqdm(range(0, len(points), config.BATCH_SIZE)):
                batch_points = points[batch_start:batch_start + config.BATCH_SIZE]
                qdrant_client.upsert(
                    collection_name=f"{config.COLLECTION_NAME_AI}",
                    points=batch_points
                )
            log.info("\n✅ Загрузка завершена!")

        except Exception as e:
            log.error(f"Ошибка при подготовке текста для эмбеддинга: {e}")
            return
        
    @staticmethod
    def get_batch_embeddings(texts: list) -> list:
        all_embeddings = []
        safe_batch_size = 5 
        for i in tqdm(range(0, len(texts), safe_batch_size), desc="Получение эмбеддингов"):
            batch = texts[i:i + safe_batch_size]
            embeddings = embeddings_qwen.embed_documents(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    @staticmethod
    def build_schema(md_text: str) -> dict[str, Any]:
        lines = md_text.splitlines()
        headings = []

        for index, line in enumerate(lines):
            match = re.match(r'^\s*#\s+(.+?)\s*$', line)
            if not match:
                continue

            title = SleepAiRagEmbeddingConfig._clean_text(match.group(1), heading=True)
            if title:
                headings.append({"title": title, "line": index, "block": ""})

        for index, heading in enumerate(headings):
            start = heading["line"] + 1
            end = headings[index + 1]["line"] if index + 1 < len(headings) else len(lines)
            heading["block"] = "\n".join(lines[start:end])

        chapter_children = SleepAiRagEmbeddingConfig._discover_chapter_children(headings)
        child_to_chapter = {
            child: chapter
            for chapter, children in chapter_children.items()
            for child in children
        }

        chapters = []
        for heading in headings:
            title = heading["title"]
            if title in child_to_chapter:
                continue

            children = chapter_children.get(title, [])
            if not children:
                children = SleepAiRagEmbeddingConfig._discover_internal_children(
                    block=heading.get("block", ""),
                    parent_title=title,
                )

            chapters.append({
                "title": title,
                "children": [
                    {"title": child}
                    for child in children
                ],
            })

        return {
            "headers_to_split_on": [
                {"markdown": header, "metadata_key": key}
                for header, key in SleepAiRagEmbeddingConfig.headers_to_split_on
            ],
            "chapter_children": chapter_children,
            "chapters": chapters,
        }

    @staticmethod
    def write_schema(file_path: Path, schema: dict[str, Any]) -> None:
        schema_path = file_path.parent / "shema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        log.info(f"Схема базы знаний записана: {schema_path}")

    @staticmethod
    def structure_text(md_text: str, schema: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if schema is None:
            schema = SleepAiRagEmbeddingConfig.build_schema(md_text)

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=SleepAiRagEmbeddingConfig.headers_to_split_on,
            strip_headers=True,
        )
        docs = splitter.split_text(SleepAiRagEmbeddingConfig._adapt_markdown_structure(md_text, schema))
        structured_docs = []

        for doc in docs:
            content = SleepAiRagEmbeddingConfig._clean_text(doc.page_content)
            if not content:
                continue

            metadata = SleepAiRagEmbeddingConfig._normalize_metadata(doc.metadata)
            structured_docs.append({
                "content": content,
                "metadata": metadata,
            })
        with open("app/support_ai/resources/RAG/knowledge_base/structured_docs.json", "w", encoding="utf-8") as f:
            json.dump(structured_docs, f, ensure_ascii=False, indent=2) 
        log.info(f"Текст структурирован через MarkdownHeaderTextSplitter: {len(structured_docs)} секций.")
        return structured_docs

    @staticmethod
    def preparation(structured_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared_docs = []

        for doc in structured_docs:
            metadata = SleepAiRagEmbeddingConfig._normalize_metadata(doc.get("metadata", {}))
            content = SleepAiRagEmbeddingConfig._clean_text(doc.get("content", ""))
            if not content:
                continue

            payload = {
                **metadata,
                "content": content,
            }
            vector_text = SleepAiRagEmbeddingConfig._build_vector_text(metadata, content)
            prepared_docs.append({
                "vector_text": vector_text,
                "payload": payload,
            })

        log.info(f"Подготовлено документов для эмбеддинга: {len(prepared_docs)}.")
        return prepared_docs

    @staticmethod
    def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, str]:
        return {
            key: SleepAiRagEmbeddingConfig._clean_text(str(metadata.get(key, "")), heading=True)
            for key in SleepAiRagEmbeddingConfig.header_order
        }

    @staticmethod
    def _build_vector_text(metadata: dict[str, str], content: str) -> str:
        context = []
        labels = {
            "chapter": "Глава",
            "subchapter": "Подглава",
            "topic": "Тема",
            "section": "Раздел",
        }

        for key in SleepAiRagEmbeddingConfig.header_order:
            value = metadata.get(key)
            if value:
                context.append(f"{labels[key]}: {value}")

        if context:
            return "\n".join(context + ["", content])
        return content

    @staticmethod
    def _clean_text(text: str, *, heading: bool = False) -> str:
        text = re.sub(r'\*\*[ \t]*!\[\]\[image\d+\][ \t]*\*\*', '', text)
        text = re.sub(r'!\[\]\[image\d+\]', '', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = text.replace('**', '')
        text = re.sub(r'\\([.\-])', r'\1', text)

        if heading:
            text = re.sub(r'[_`]+', '', text)
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _discover_chapter_children(headings: list[dict[str, Any]]) -> dict[str, list[str]]:
        def has_duplicate_title(heading: dict[str, Any]) -> bool:
            duplicate_pattern = re.escape(heading["title"])
            return bool(re.search(rf'(?im)^\s*\*\*{duplicate_pattern}\*\*\s*$', heading.get("block", "")))

        def has_container_intro(heading: dict[str, Any]) -> bool:
            return bool(re.search(r'(?im)^\s*#{2,4}\s+\*{0,2}\s*инструкция\b', heading.get("block", "")))

        def has_detailed_markdown_intro(heading: dict[str, Any]) -> bool:
            return bool(re.search(r'(?im)^\s*#{2,4}\s+\*{0,2}\s*подробная инструкция\b', heading.get("block", "")))

        def looks_like_standalone_chapter(heading: dict[str, Any]) -> bool:
            block = heading.get("block", "")
            if has_detailed_markdown_intro(heading):
                return True
            if re.search(r'(?im)^\s*\*\*подробная инструкция\b', block):
                return False
            return has_duplicate_title(heading)

        def starts_child_group(index: int) -> bool:
            next_heading = headings[index + 1] if index + 1 < len(headings) else None
            if not next_heading:
                return False

            current_title = headings[index]["title"].casefold()
            next_title = next_heading["title"].casefold()
            if next_title == current_title or next_title.startswith(f"{current_title} "):
                return True

            if looks_like_standalone_chapter(next_heading):
                return False

            next_after_child = headings[index + 2] if index + 2 < len(headings) else None
            return bool(next_after_child) and not looks_like_standalone_chapter(next_after_child)

        def is_active_parent_boundary(index: int) -> bool:
            heading = headings[index]
            return (
                has_detailed_markdown_intro(heading)
                or (index == len(headings) - 1 and has_duplicate_title(heading))
                or (starts_child_group(index) and has_container_intro(heading))
            )

        chapter_children: dict[str, list[str]] = {}
        active_parent = ""

        for index, heading in enumerate(headings):
            title = heading["title"]

            if active_parent:
                if not is_active_parent_boundary(index):
                    chapter_children[active_parent].append(title)
                    continue

            if starts_child_group(index):
                active_parent = title
                chapter_children.setdefault(title, [])
                continue

            active_parent = ""

        return {
            chapter: children
            for chapter, children in chapter_children.items()
            if children
        }

    @staticmethod
    def _discover_internal_children(block: str, parent_title: str) -> list[str]:
        children = []
        seen = set()

        heading_patterns = [
            r'(?im)^\s*#{2,6}\s+(.+?)\s*$',
            r'(?im)^\s*\d+\\?[\.)]\s+\*\*([^*\n]{1,140})\*\*.*$',
            r'(?im)^\s*\d+\\?[\.)]\s+([А-ЯЁ][^.\n]{3,90})\s*$',
            r'(?im)^\s*\*\*([^*\n]{1,140})\*\*\s*$',
        ]

        for pattern in heading_patterns:
            for match in re.finditer(pattern, block):
                title = SleepAiRagEmbeddingConfig._clean_text(match.group(1), heading=True).rstrip(":")
                normalized = title.lower().strip(" :")

                if not title or normalized in seen:
                    continue
                if normalized == parent_title.lower().strip(" :"):
                    continue
                if normalized.startswith("подробная инструкция") or normalized.startswith("инструкция"):
                    continue
                if len(title) > 90:
                    continue
                if normalized.startswith((
                    "нажмите",
                    "заполните",
                    "кликните",
                    "выберите",
                    "перейдите",
                    "в открывшемся",
                )):
                    continue
                if title.startswith("![]"):
                    continue

                seen.add(normalized)
                children.append(title)

        return children

    @staticmethod
    def _adapt_markdown_structure(text: str, schema: dict[str, Any]) -> str:
        def number_depth(title: str) -> int:
            match = re.match(r'^\d+(?:\.\d+)*\.?', title)
            return match.group(0).rstrip(".").count(".") + 1 if match else 0

        def is_intro_title(title: str) -> bool:
            normalized = title.lower().strip(" :")
            return (
                normalized.startswith("инструкция по работе")
                or normalized.startswith("подробная инструкция")
                or normalized == "инструкция"
                or normalized.startswith("инструкция по разделу")
            )

        def is_block_container(title: str) -> bool:
            normalized = title.lower().strip(" :")
            return (
                normalized.startswith("основные блоки")
                or normalized.startswith("карточка ")
                or normalized.startswith("индивидуальная вкладка")
            )

        def format_header(level: int, title: str) -> str:
            return f"{'#' * min(max(level, 1), 4)} {title}"

        def update_current_titles(level: int, title: str) -> None:
            header_key = SleepAiRagEmbeddingConfig.header_order[level - 1]
            current_titles[header_key] = title
            for lower_key in SleepAiRagEmbeddingConfig.header_order[level:]:
                current_titles[lower_key] = ""

        def resolve_markdown_header_level(raw_level: int, title: str) -> tuple[int, str]:
            nonlocal active_parent_chapter

            if raw_level == 1:
                if title in child_to_chapter:
                    active_parent_chapter = child_to_chapter[title]
                    return 2, active_parent_chapter

                active_parent_chapter = title if title in chapter_children else ""
                return 1, active_parent_chapter

            if raw_level == 2 and current_titles["subchapter"]:
                return 3, active_parent_chapter

            if raw_level == 4 and current_titles["subchapter"] and not current_titles["topic"]:
                return 3, active_parent_chapter

            return min(raw_level, 4), active_parent_chapter

        def resolve_bold_heading_level(title: str) -> int | None:
            if is_intro_title(title):
                return None

            depth = number_depth(title)
            if depth == 1:
                if number_depth(current_titles["topic"]) >= 2 or is_block_container(current_titles["topic"]):
                    return 4
                return 3

            if depth >= 2:
                if current_titles["topic"] and not number_depth(current_titles["topic"]):
                    return 4
                return 3

            if title.endswith(":"):
                return 4

            if number_depth(current_titles["topic"]) >= 2 or is_block_container(current_titles["topic"]):
                return 4

            return 3

        lines = []
        current_titles = {key: "" for key in SleepAiRagEmbeddingConfig.header_order}
        active_parent_chapter = ""
        chapter_children = schema.get("chapter_children", {})
        child_to_chapter = {
            child: chapter
            for chapter, children in chapter_children.items()
            for child in children
        }

        for raw_line in text.splitlines():
            line = raw_line.rstrip()

            numbered_bold_match = re.match(r'^\s*\d+\\?\.\s+\*\*(?P<title>[^*\n]{1,140}?)\*\*', line)
            if numbered_bold_match and (
                current_titles["subchapter"]
                or is_block_container(current_titles["topic"])
            ):
                title = SleepAiRagEmbeddingConfig._clean_text(numbered_bold_match.group("title"), heading=True)
                if title:
                    level = 4 if is_block_container(current_titles["topic"]) else 3
                    lines.append(format_header(level, title))
                    update_current_titles(level, title)
                continue

            numbered_header_match = re.match(r'^\s*\d+[\.)]\s+(#{1,6})\s*(.*?)\s*$', line)
            if numbered_header_match:
                title = SleepAiRagEmbeddingConfig._clean_text(numbered_header_match.group(2), heading=True)
                if title:
                    lines.append(format_header(4, title))
                    update_current_titles(4, title)
                continue

            header_match = re.match(r'^\s*(#{1,6})\s*(.*?)\s*$', line)
            if header_match:
                title = SleepAiRagEmbeddingConfig._clean_text(header_match.group(2), heading=True)
                if title:
                    level, active_parent_chapter = resolve_markdown_header_level(len(header_match.group(1)), title)
                    lines.append(format_header(level, title))
                    update_current_titles(level, title)
                continue

            bold_match = re.match(r'^\s*\*\*(?P<title>[^*\n]{1,140}?)\*\*\s*$', line)
            if bold_match:
                title = SleepAiRagEmbeddingConfig._clean_text(bold_match.group("title"), heading=True)
                if not title:
                    continue
                if title in current_titles.values():
                    continue

                level = resolve_bold_heading_level(title)
                if level:
                    title = title.rstrip(":")
                    lines.append(format_header(level, title))
                    update_current_titles(level, title)
                else:
                    lines.append(title)
                continue

            lines.append(line)

        return "\n".join(lines)
    
    @staticmethod
    def clear(file_path: Path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        cleaned_content = content.replace('\x00', '')
        cleaned_content = re.sub(r'\*\*[ \t]*!\[\]\[image\d+\][ \t]*\*\*', '', cleaned_content)
        cleaned_content = re.sub(r'!\[\]\[image\d+\]', '', cleaned_content)
        cleaned_content = re.sub(
            r'(?ms)^[ \t]*\[image\d+\]:.*\Z',
            '',
            cleaned_content
        )
        cleaned_content = re.sub(r'[ \t]+\n', '\n', cleaned_content)
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content).strip()
        log.info(f"Файл {file_path.name} очищен от мусорных данных.")
        return cleaned_content
            
if __name__ == "__main__":
    SleepAiRagEmbeddingConfig.run_qdrant_pipeline(
        file_path=Path("app/support_ai/resources/RAG/knowledge_base/Железяки.Описание работы.md")
    )
