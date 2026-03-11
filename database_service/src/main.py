import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # вывод в консоль
    ]
)


from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from typing import AsyncGenerator   
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import init_db_create_all, get_async_session
from routers.members_router import router as members_router
from routers.wishes_router import router as wishes_router
from routers.posts_router import router as posts_router
from routers.events_router import router as events_router
from routers.site_config_router import router as site_config_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.info("Application starting up...")
    await init_db_create_all()
    logging.info("Database initialized")

    app.include_router(members_router)
    app.include_router(wishes_router)
    app.include_router(posts_router)
    app.include_router(events_router)
    app.include_router(site_config_router)

    try:
        yield
    finally:
        logging.info("Application shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.get('/health')
    async def health_check(db: AsyncSession = Depends(get_async_session)):
        return {'status': 'ok'}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    # log_config=LOGGING_CONFIG гарантирует, что uvicorn использует наш конфиг
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
