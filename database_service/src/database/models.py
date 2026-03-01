from sqlalchemy import (
    Column, Integer, String, Boolean, 
    Enum, Time, ForeignKey, DateTime, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from database.db import Base

from enums import Role, ParseMod, Day


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    second_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    tg_username = Column(String, unique=True, index=True)

    # enum_role
    role = Column(Enum(Role, name="role_enum"), nullable=False, default=Role.FAMALY_HEAD)

    is_main_account = Column(Boolean, nullable=False)  # глава семьи
    is_going_on_event = Column(Boolean, nullable=False)  # присутствие на свадьбе

        # one-to-one relationship: Member.wish -> Wish
    wish = relationship("Wish", uselist=False, back_populates="member", cascade="all, delete-orphan")


class Wish(Base):
    __tablename__ = "wishes"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), unique=True, nullable=False)
    wish_text = Column(String, nullable=False)

    # list[str]
    drinks = Column(ARRAY(String), nullable=True)

    member = relationship("Member", back_populates="wish")


class PreparedPost(Base):
    __tablename__ = "prepared_posts"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    parse_mode = Column(Enum(ParseMod, name="parse_mod_enum"), nullable=False, default=ParseMod.MARKDOWN)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(Enum(Day, name="day_enum"), nullable=False)
    ivent_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    time = Column(Time, nullable=False)


class SiteConfig(Base):
    __tablename__ = "site_config"

    id = Column(Integer, primary_key=True, index=True)
    config = Column(JSONB, nullable=False)  # основной JSON payload
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<SiteConfig id={self.id}>"
