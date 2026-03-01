from pydantic import BaseModel, field_validator, ConfigDict
import re
from typing import Optional


class MemberCreate(BaseModel):
    first_name: str
    second_name: str
    phone_number: str
    tg_username: Optional[str] = None
    role: str
    main_account: Optional[int] = None
    is_main_account: bool
    is_going_on_event: bool

    @field_validator("tg_username")
    @classmethod
    def validate_tg_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v.startswith("@"):
            raise ValueError("tg_username must start with '@'")
        if not re.match(r"^@[A-Za-z0-9_]{1,}$", v):
            raise ValueError("tg_username contains invalid characters")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("phone_number is required")
        digits = re.sub(r"\D", "", v)
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("phone_number must contain between 7 and 15 digits")
        return v


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    second_name: str
    phone_number: str
    tg_username: Optional[str] = None
    role: str
    main_account: Optional[int] = None
    is_main_account: bool
    is_going_on_event: bool
