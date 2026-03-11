import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import Depends

from repositories.site_config_repository import SiteConfigRepository, get_site_config_repository
from schemas.site_config_schema import SiteConfigIn
from database.models import SiteConfig



class SiteConfigService:
    def __init__(self, repo: SiteConfigRepository):
        self.repo = repo

    async def save_config(self, data: SiteConfigIn) -> SiteConfig:
        logging.info("Saving new site config, keys=%s", list(data.config.keys()))
        config = await self.repo.save_config(data)
        logging.info("Site config saved: id=%s, updated_at=%s", config.id, config.updated_at)
        return config

    async def get_latest_config(self) -> Dict[str, Any]:
        logging.info("Fetching latest site config")
        config = await self.repo.get_latest_config()
        if config is None:
            logging.warning("No site config found in database")
            raise ValueError("No site config found")
        logging.info("Latest site config found: id=%s, updated_at=%s", config.id, config.updated_at)
        return config.config

    async def delete_all_except_latest(self) -> int:
        logging.info("Deleting all site configs except the latest")
        latest = await self.repo.get_latest_config()
        if latest is None:
            logging.warning("No site config found, nothing to delete")
            raise ValueError("No site config found")
        deleted_count = await self.repo.delete_all_except_latest()
        logging.info("Deleted %d site config(s), kept id=%s", deleted_count, latest.id)
        return deleted_count


async def get_site_config_service(
    repo: SiteConfigRepository = Depends(get_site_config_repository),
) -> AsyncGenerator[SiteConfigService, None]:
    yield SiteConfigService(repo)
