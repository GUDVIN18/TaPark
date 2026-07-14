from typing import Dict, Optional
from langchain_core.output_parsers import JsonOutputParser
from app.support_ai.resources.schemas import (
    SupportAi,
    IntentClassifier,
    DynemicRagContext,
)


parser_main_llm = JsonOutputParser(pydantic_object=SupportAi)
parser_intent_classifier = JsonOutputParser(pydantic_object=IntentClassifier)
parcer_rag_context = JsonOutputParser(pydantic_object=DynemicRagContext)