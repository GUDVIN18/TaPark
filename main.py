from app.include.logging_config import logger as log
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from app.router import main_router
from app.include.events import Events
import uvicorn


log.success("Starting TA-Park support AI...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Events(have_db=True, exit_on_fail=True).get_startup()()
    yield
    await Events(have_db=True, exit_on_fail=True).get_shutdown()()

app = FastAPI(
    lifespan=lifespan,
    title="TA-Park AI",
    version="beta 0.0.1",
    openapi_tags=[{"name": "AI", "description": "Взаимодействие с AI Support TA-Park."}],
    dependencies=[
        Depends(APIKeyHeader(name='Secret', scheme_name='api_secret', auto_error=False))
    ],
)
app.include_router(main_router)
app.mount("/front", StaticFiles(directory="app/front", html=True), name="front")

if __name__ == "__main__":
    log.info("Starting debug uvicorn")
    uvicorn.run(
        "app.main:app",
        host='0.0.0.0',
        port=8881,
        reload=True,
        workers=1,
        log_level='debug',
    )
    log.info("Uvicorn stopped")
