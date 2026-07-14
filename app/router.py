from fastapi import APIRouter
from .support_ai.router import router as incidents_router

main_router = APIRouter()


main_router.include_router(
    incidents_router,
    tags=["SupportAI Pipline"],
    prefix='/ai'
)

