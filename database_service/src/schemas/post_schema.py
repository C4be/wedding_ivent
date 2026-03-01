from typing import Optional
from pydantic import BaseModel, Field, field_validator

from enums import ParseMod


class PreparedPostBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    parse_mode: ParseMod = ParseMod.MARKDOWN

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class PreparedPostCreate(PreparedPostBase):
    """Payload for creating a prepared post."""
    pass


class PreparedPostUpdate(BaseModel):
    """Partial update payload."""
    text: Optional[str] = Field(None, min_length=1, max_length=5000)
    parse_mode: Optional[ParseMod] = None

    @field_validator("text")
    @classmethod
    def strip_text_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip()


class PreparedPostRead(PreparedPostBase):
    id: int

    class Config:
        orm_mode = True
        json_encoders = {ParseMod: lambda v: v.value}
