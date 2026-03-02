from __future__ import annotations
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = []

    LOG_DIR: str = "./logs"
    DB_SERVICE_HOST: str
    DB_SERVICE_PORT: int

    @property
    def DB_SERVICE_URL(self) -> str:
        return f"http://{self.DB_SERVICE_HOST}:{self.DB_SERVICE_PORT}"

    @field_validator("ADMIN_IDS", mode="before")
    def _parse_admin_ids(cls, v):
        # Accept comma-separated string, single int, or already-parsed list
        if isinstance(v, str):
            # "1,2,3" or "1163267317"
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, int):
            return [v]
        return v
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding="utf-8",
    )


settings = Settings()
