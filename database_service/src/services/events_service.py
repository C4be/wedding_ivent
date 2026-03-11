import logging

from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.events_repository import EventsRepository, get_events_repository
from schemas.event_schema import EventCreate
from database.models import Event
from enums import Day


class EventsService:
    def __init__(self, repo: EventsRepository):
        self.repo = repo

    async def add_event(self, data: EventCreate) -> Event:
        logging.info("Adding event: name='%s', day=%s, time=%s", data.ivent_name, data.day, data.time)
        event = await self.repo.add_event(data)
        logging.info("Event added: id=%s", event.id)
        return event

    async def delete_event(self, event_id: int) -> bool:
        logging.info("Deleting event: id=%s", event_id)
        deleted = await self.repo.delete_event(event_id)
        if not deleted:
            logging.warning("Event not found for deletion: id=%s", event_id)
            raise ValueError(f"Event with id={event_id} not found")
        logging.info("Event deleted: id=%s", event_id)
        return True

    async def get_events_by_day(self, day: Day) -> List[Event]:
        logging.info("Fetching events for day=%s", day)
        events = await self.repo.get_events_by_day(day)
        logging.info("Fetched %d events for day=%s", len(events), day)
        return events

    async def get_all_events(self) -> List[Event]:
        logging.info("Fetching all events")
        events = await self.repo.get_all_events()
        logging.info("Fetched %d events total", len(events))
        return events


async def get_events_service(
    repo: EventsRepository = Depends(get_events_repository),
) -> AsyncGenerator[EventsService, None]:
    yield EventsService(repo)
