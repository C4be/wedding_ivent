from typing import AsyncGenerator, Optional

from fastapi import Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_async_session
from database.models import SiteConfig
from schemas.site_config_schema import SiteConfigIn


class SiteConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 1. Сохранить новый конфиг
    async def save_config(self, data: SiteConfigIn) -> SiteConfig:
        config = SiteConfig(config=data.config)
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    # 2. Получить последний конфиг по времени
    async def get_latest_config(self) -> Optional[SiteConfig]:
        result = await self.session.execute(
            select(SiteConfig).order_by(SiteConfig.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    # 3. Удалить все конфиги кроме последнего
    async def delete_all_except_latest(self) -> int:
        latest = await self.get_latest_config()
        if latest is None:
            return 0
        result = await self.session.execute(
            delete(SiteConfig).where(SiteConfig.id != latest.id)
        )
        await self.session.commit()
        return result.rowcount


async def get_site_config_repository(
    db: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SiteConfigRepository, None]:
    yield SiteConfigRepository(db)
