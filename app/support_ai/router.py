import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.engine import Connection
from typing import List, Dict, Any
from .resources.schemas.support import (
    ResponseSupportAi, 
    UploadSupportAi, 
    SupportAi
)
from .resources.pipline import geration_pipe
from app.include.logging_config import logger as log
from ..include.permissions import secret_access
from .resources.exceptions import SupportAiErrorGeneration


router = APIRouter()

@router.post(
    "/chat",
    response_model=ResponseSupportAi,
    dependencies=[Depends(secret_access)],
    name="Задать вопрос и получить ответ",
)
async def support(
    data: UploadSupportAi,
):
    log.success(f"{data.user_id}: QUESTION {data=}")
    try:
        support_ai_answer: SupportAi = await geration_pipe(data=data)
        return ResponseSupportAi(
            message=support_ai_answer.answer,
            # buttons=support_ai_answer.buttons
        )
    except Exception as e:
        log.error(f"Unhandled error in /chat endpoint: {e}")
        raise SupportAiErrorGeneration

@router.post(
    "/upload/kb",
    response_model=str,
    dependencies=[Depends(secret_access)],
    name="Загрузка базы знаний для RAG и обновление векторов",
)
async def upload_kb(
    file: UploadFile = File(...),
):
    # Проверка расширения
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="Допускаются только файлы формата .md",
        )
    content = await file.read()
    text = content.decode("utf-8")
    log.info(f"{text=}")
    return "OK"