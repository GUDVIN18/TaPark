from fastapi import APIRouter
from .support_ai.router import router as incidents_router
from .usedesc.router import router as usedesc_router

main_router = APIRouter()


main_router.include_router(
    incidents_router,
    tags=["SupportAI Pipline"],
    prefix='/ai'
)

main_router.include_router(
    usedesc_router,
    tags=["Usedesk"],
    prefix="/usedesc",
)
