from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from services.events_service import EventsService, get_events_service
from schemas.event_schema import EventCreate, EventRead
from enums import Day

router = APIRouter(prefix="/events", tags=["Events"])


# 1. Добавить ивент
@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def add_event(
    data: EventCreate,
    service: EventsService = Depends(get_events_service),
):
    return await service.add_event(data)


# 2. Удалить ивент по id
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    service: EventsService = Depends(get_events_service),
):
    try:
        await service.delete_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 3. Получить все ивенты по конкретному дню
@router.get("/by-day/{day}", response_model=List[EventRead])
async def get_events_by_day(
    day: Day,
    service: EventsService = Depends(get_events_service),
):
    return await service.get_events_by_day(day)


# 4. Получить все ивенты
@router.get("/", response_model=List[EventRead])
async def get_all_events(
    service: EventsService = Depends(get_events_service),
):
    return await service.get_all_events()
