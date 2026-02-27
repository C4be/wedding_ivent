from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class Member:
    id: Optional[int]
    telegram_id: Optional[int]
    full_name: str
    partner_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    attendance_day1: int
    attendance_day2: int
    drink_pref: Optional[str]
    wishes: Optional[str]
    created_at: Optional[datetime] = None


@dataclass
class GalleryLink:
    id: Optional[int]
    url: str
    caption: Optional[str]
    added_by: Optional[int]


@dataclass
class MessageTemplate:
    id: Optional[int]
    title: str
    body: str
