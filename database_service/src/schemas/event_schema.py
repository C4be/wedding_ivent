from __future__ import annotations
from datetime import time, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from enums import Day


class EventBase(BaseModel):
    day: Day = Field(..., description="День события (enum Day)")
    ivent_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    time: time = Field(..., description="Время в формате HH:MM")

    @field_validator("ivent_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ivent_name must not be empty")
        return v

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must not be empty")
        return v

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v) -> time:
        """
        Accepts:
         - datetime.time
         - string "HH:MM" or "HH:MM:SS"
         - datetime (will take .time())
        """
        if v is None:
            raise ValueError("time is required")
        if isinstance(v, time):
            return v
        if isinstance(v, datetime):
            return v.time()
        if isinstance(v, str):
            v = v.strip()
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(v, fmt).time()
                except ValueError:
                    continue
        raise ValueError("time must be a time or string in format HH:MM")


    @field_validator("day")
    @classmethod
    def validate_day(cls, v) -> Day:
        """
        Accepts Day or string (either enum value or name), returns Day.
        """
        if isinstance(v, Day):
            return v
        if isinstance(v, str):
            s = v.strip()
            # try by value
            for member in Day:
                if s == member.value or s.lower() == member.name.lower():
                    return member
        raise ValueError(f"invalid Day value: {v}")


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    day: Optional[Day] = None
    ivent_name: Optional[str] = None
    description: Optional[str] = None
    time: Optional[time] = None

    @field_validator("ivent_name")
    @classmethod
    def strip_name_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("ivent_name must not be empty")
        return v

    @field_validator("description")
    @classmethod
    def strip_description_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("description must not be empty")
        return v

    @field_validator("time", mode="before")
    @classmethod
    def parse_time_optional(cls, v) -> Optional[time]:
        if v is None:
            return None
        if isinstance(v, time):
            return v
        if isinstance(v, datetime):
            return v.time()
        if isinstance(v, str):
            v = v.strip()
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(v, fmt).time()
                except ValueError:
                    continue
        raise ValueError("time must be a time or string in format HH:MM")


class EventRead(EventBase):
    id: int

    class Config:
        orm_mode = True
        json_encoders = {
            time: lambda v: v.strftime("%H:%M"),
            Day: lambda v: v.value
        }