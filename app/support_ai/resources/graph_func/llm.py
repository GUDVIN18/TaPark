import os
from pathlib import Path
from app.include.config import config
from langchain_qwq import ChatQwQ
from app.include.logging_config import logger as log


BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(f"BASE_DIR: {BASE_DIR}")
try:
    SYSTEM_INSTRUCTION = (BASE_DIR / "context" / "agent_instruction.txt").read_text(encoding="utf-8")
except Exception as e:
    log.error(f"Failed to load prompts: {e}")

llm_analytics = ChatQwQ(
    api_key=config.QWEN_API_KEY,
    model=config.ANALYTICS_MODEL_AI,
    temperature=0.05,
    top_p=0.9,
    extra_body={
        "enable_thinking": False,
    },
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