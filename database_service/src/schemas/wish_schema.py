from typing import List, Optional
from pydantic import BaseModel, field_validator


class WishBase(BaseModel):
    wish_text: str
    drinks: Optional[List[str]] = None

    @field_validator("wish_text")
    @classmethod
    def validate_wish_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("wish_text must not be empty")
        return v

    @field_validator("drinks", mode="before")
    @classmethod
    def normalize_drinks(cls, v):
        """
        Принимает либо список строк, либо строку с запятой.
        Нормализует в List[str] или None.
        """
        if v is None:
            return None
        if isinstance(v, str):
            items = [s.strip() for s in v.split(",") if s.strip()]
            return items or None
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()] or None
        raise ValueError("drinks must be a list of strings or a comma-separated string")

    @field_validator("drinks")
    @classmethod
    def validate_drink_items(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        for item in v:
            if not item:
                raise ValueError("drink items must be non-empty strings")
            if len(item) > 200:
                raise ValueError("drink item is too long")
        return v


class WishCreate(WishBase):
    # member_id можно указывать при создании (если создаём отдельно), 
    # но часто wish создают через member-relation — тогда member_id не обязателен.
    member_id: Optional[int] = None


class WishUpdate(BaseModel):
    wish_text: Optional[str] = None
    drinks: Optional[List[str]] = None

    @field_validator("wish_text")
    @classmethod
    def validate_wish_text_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("wish_text must not be empty")
        return v

    @field_validator("drinks", mode="before")
    @classmethod
    def normalize_drinks_optional(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            items = [s.strip() for s in v.split(",") if s.strip()]
            return items or None
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()] or None
        raise ValueError("drinks must be a list of strings or a comma-separated string")


class WishRead(WishBase):
    id: int
    member_id: int

    class Config:
        orm_mode = True