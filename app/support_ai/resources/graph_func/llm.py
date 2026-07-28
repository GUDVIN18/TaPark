import os
from pathlib import Path
from app.include.config import config
from langchain_qwq import ChatQwQ
from app.include.logging_config import logger as log


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTEXT_DIR = BASE_DIR / "prompts"
PROMPT_FILES = (
    "company.md",
    "system.md",
    "fallback.md",
    "response_style.md",
)

try:
    SYSTEM_INSTRUCTION = "\n\n".join(
        (CONTEXT_DIR / file_name).read_text(encoding="utf-8").strip()
        for file_name in PROMPT_FILES
    )
except Exception:
    log.exception("Failed to load prompt files")
    raise

llm_analytics = ChatQwQ(
    api_key=config.QWEN_API_KEY,
    model=config.ANALYTICS_MODEL_AI,
    temperature=0.05,
    top_p=0.9,
    extra_body={
        "enable_thinking": False,
    },
    # max_tokens=3000
)
main_llm=ChatQwQ(
    api_key=config.QWEN_API_KEY,
    model=config.MODEL_AI,
    temperature=0.2,
    top_p=0.95,
    extra_body={
        "enable_thinking": False,
        # "thinking_budget": 50,
    },
)
