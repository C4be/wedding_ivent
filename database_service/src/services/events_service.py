from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.events_repository import EventsRepository, get_events_repository
from schemas.event_schema import EventCreate
from database.models import Event
from enums import Day


class EventsService:
    def __init__(self, repo: EventsRepository):
        self.repo = repo

    # 1. Добавить ивент
    async def add_event(self, data: EventCreate) -> Event:
        return await self.repo.add_event(data)

    # 2. Удалить ивент по id
    async def delete_event(self, event_id: int) -> bool:
        deleted = await self.repo.delete_event(event_id)
        if not deleted:
            raise ValueError(f"Event with id={event_id} not found")
        return True

    # 3. Получить все ивенты по конкретному дню
    async def get_events_by_day(self, day: Day) -> List[Event]:
        return await self.repo.get_events_by_day(day)

    # 4. Получить все ивенты
    async def get_all_events(self) -> List[Event]:
        return await self.repo.get_all_events()


async def get_events_service(
    repo: EventsRepository = Depends(get_events_repository),
) -> AsyncGenerator[EventsService, None]:
    yield EventsService(repo)
