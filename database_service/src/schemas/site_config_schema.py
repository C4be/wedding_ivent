from __future__ import annotations
from typing import Any, Dict
from datetime import datetime
from pydantic import BaseModel


class SiteConfigIn(BaseModel):
    config: Dict[str, Any]


class SiteConfigOut(BaseModel):
    id: int
    config: Dict[str, Any]
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }