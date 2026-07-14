from app.include.logging_config import logger as log
from fastapi import Depends, FastAPI
from fastapi.security import APIKeyHeader
from app.router import main_router
import uvicorn


log.success("Starting TA-Park support AI...")
app = FastAPI(
    title="TA-Park AI",
    version="beta 0.0.1",
    openapi_tags=[{"name": "AI", "description": "Взаимодействие с AI Support TA-Park."}],
    dependencies=[
        Depends(APIKeyHeader(name='Secret', scheme_name='api_secret', auto_error=False))
    ],
)
app.include_router(main_router)

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
