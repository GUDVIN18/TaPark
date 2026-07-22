from pathlib import Path
import datetime as dt
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File


KNOWLEDGE_BASE_DIR = Path("app/support_ai/resources/RAG/knowledge_base")
UPLOAD_DIR = KNOWLEDGE_BASE_DIR / "upload"

def _safe_upload_name(filename: str) -> str:
    source_name = Path(filename).name
    stem = Path(source_name).stem
    suffix = Path(source_name).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-zА-Яа-яЁё0-9_.-]+", "_", stem).strip("._")
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_stem or 'knowledge_base'}_{timestamp}{suffix}"


def _resolve_uploaded_md(path: str) -> Path:
    file_path = Path(path)
    if file_path.is_absolute():
        raise HTTPException(status_code=400, detail="Передайте относительный путь до файла")

    resolved_path = (Path.cwd() / file_path).resolve()
    upload_root = (Path.cwd() / UPLOAD_DIR).resolve()

    if upload_root not in resolved_path.parents:
        raise HTTPException(status_code=400, detail="Файл должен находиться в папке upload")
    if resolved_path.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Допускаются только файлы формата .md")
    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")

    return resolved_path