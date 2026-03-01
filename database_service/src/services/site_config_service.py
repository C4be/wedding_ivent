from typing import Any, AsyncGenerator, Dict

from fastapi import Depends

from repositories.site_config_repository import SiteConfigRepository, get_site_config_repository
from schemas.site_config_schema import SiteConfigIn
from database.models import SiteConfig


class SiteConfigService:
    def __init__(self, repo: SiteConfigRepository):
        self.repo = repo

    # 1. Загрузить новый конфиг
    async def save_config(self, data: SiteConfigIn) -> SiteConfig:
        return await self.repo.save_config(data)

    # 2. Получить последний конфиг в виде dict
    async def get_latest_config(self) -> Dict[str, Any]:
        config = await self.repo.get_latest_config()
        if config is None:
            raise ValueError("No site config found")
        return config.config

    # 3. Удалить все конфиги кроме последнего
    async def delete_all_except_latest(self) -> int:
        latest = await self.repo.get_latest_config()
        if latest is None:
            raise ValueError("No site config found")
        return await self.repo.delete_all_except_latest()


async def get_site_config_service(
    repo: SiteConfigRepository = Depends(get_site_config_repository),
) -> AsyncGenerator[SiteConfigService, None]:
    yield SiteConfigService(repo)
