from typing import AsyncGenerator, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_async_session
from database.models import Event
from schemas.event_schema import EventCreate
from enums import Day


class EventsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 1. Добавить ивент
    async def add_event(self, data: EventCreate) -> Event:
        event = Event(**data.model_dump())
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    # 2. Удалить ивент по id
    async def delete_event(self, event_id: int) -> bool:
        event = await self.session.get(Event, event_id)
        if event is None:
            return False
        await self.session.delete(event)
        await self.session.commit()
        return True

    # 3. Получить все ивенты по конкретному дню
    async def get_events_by_day(self, day: Day) -> List[Event]:
        result = await self.session.execute(
            select(Event).where(Event.day == day).order_by(Event.time)
        )
        return list(result.scalars().all())

    # 4. Получить все ивенты
    async def get_all_events(self) -> List[Event]:
        result = await self.session.execute(
            select(Event).order_by(Event.day, Event.time)
        )
        return list(result.scalars().all())


async def get_events_repository(
    db: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[EventsRepository, None]:
    yield EventsRepository(db)
