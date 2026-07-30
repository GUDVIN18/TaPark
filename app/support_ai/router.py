import asyncio
import datetime as dt
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from .resources.schemas.support import (
    UploadSupportAi, 
    SupportAi,
    UpdateKbRequest,
)
from .resources.pipline import geration_pipe
from app.include.logging_config import logger as log
from ..include.permissions import secret_access
from .resources.exceptions import SupportAiErrorGeneration
from .resources.service import (
    _safe_upload_name, 
    _resolve_uploaded_md,
    KNOWLEDGE_BASE_DIR,
    UPLOAD_DIR,
)


router = APIRouter()

@router.post(
    "/chat",
    response_model=SupportAi,
    dependencies=[Depends(secret_access)],
    name="Задать вопрос и получить ответ",
)
async def support(
    data: UploadSupportAi,
) -> SupportAi:
    log.success(f"{data.user_id}: QUESTION {data=}")
    try:
        support_ai_answer: SupportAi = await geration_pipe(data=data)
        return support_ai_answer
    except Exception as e:
        log.error(f"Unhandled error in /chat endpoint: {e}")
        raise SupportAiErrorGeneration

@router.post(
    "/upload/kb",
    response_model=str,
    dependencies=[Depends(secret_access)],
    name="Загрузка файла базы знаний",
)
async def upload_kb(
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="Допускаются только файлы формата .md",
        )

    content = await file.read()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload_path = UPLOAD_DIR / _safe_upload_name(file.filename)
    upload_path.write_bytes(content)

    return upload_path.resolve().relative_to(Path.cwd().resolve()).as_posix()


@router.get(
    "/kb/files",
    response_model=list[str],
    dependencies=[Depends(secret_access)],
    name="Получить список загруженных файлов базы знаний",
)
async def get_kb_files():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        UPLOAD_DIR.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [
        path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        for path in files
        if path.is_file()
    ]


@router.post(
    "/update/kb",
    response_model=str,
    dependencies=[Depends(secret_access)],
    name="Обновление Qdrant и векторов RAG",
)
async def update_kb(data: UpdateKbRequest):
    from .resources.RAG.qdrant_loader import SleepAiRagEmbeddingConfig

    file_path = _resolve_uploaded_md(data.path)
    await asyncio.to_thread(
        SleepAiRagEmbeddingConfig.run_qdrant_pipeline,
        file_path=file_path,
    )
    return f"Qdrant обновлен из файла: {file_path.resolve().relative_to(Path.cwd().resolve()).as_posix()}"



    
