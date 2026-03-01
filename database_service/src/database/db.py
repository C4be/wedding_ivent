from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator

from config import db_config, app_config

DATABASE_URL = db_config.dsn

engine = create_async_engine(
    DATABASE_URL,
    echo=app_config.debug,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,  # autocommit deprecated but keep False
)

Base = declarative_base()

async def init_db_create_all():
    """
    Для разработки: создаёт отсутствующие таблицы асинхронно.
    Использует run_sync для вызова sync create_all.
    Не перезаписывает существующие таблицы.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный поставщик сессии.
    Использовать в FastAPI как dependency:
        async def endpoint(db: AsyncSession = Depends(get_async_session)):
            ...
    По завершении — коммит; при исключении — rollback.
    Если вам не нужен автоматический коммит, уберите await session.commit().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise