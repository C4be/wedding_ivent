from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from services.members_service import MembersService, get_members_service
from schemas.member_schema import MemberCreate, MemberRead

router = APIRouter(prefix="/members", tags=["Members"])


# 1. Добавить одного пользователя
@router.post("/", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    data: MemberCreate,
    service: MembersService = Depends(get_members_service),
):
    return await service.add_member(data)


# 2. Добавить нескольких пользователей (семью)
@router.post("/family", response_model=List[MemberRead], status_code=status.HTTP_201_CREATED)
async def add_members(
    members_data: List[MemberCreate],
    service: MembersService = Depends(get_members_service),
):
    try:
        return await service.add_members(members_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 3. Удалить пользователя по id
@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    service: MembersService = Depends(get_members_service),
):
    try:
        await service.delete_member(member_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 4а. Обновить номер телефона
@router.patch("/{member_id}/phone", response_model=MemberRead)
async def update_phone_number(
    member_id: int,
    phone_number: str,
    service: MembersService = Depends(get_members_service),
):
    try:
        return await service.update_phone_number(member_id, phone_number)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 4б. Обновить статус присутствия
@router.patch("/{member_id}/going", response_model=MemberRead)
async def update_going_on_event(
    member_id: int,
    is_going: bool,
    service: MembersService = Depends(get_members_service),
):
    try:
        return await service.update_going_on_event(member_id, is_going)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 5. Получить список всех пользователей
@router.get("/", response_model=List[MemberRead])
async def get_all_members(
    service: MembersService = Depends(get_members_service),
):
    return await service.get_all_members()


# 6. Получить семью по имени и фамилии любого участника
@router.get("/family/search", response_model=List[MemberRead])
async def get_family_by_name(
    first_name: str,
    second_name: str,
    service: MembersService = Depends(get_members_service),
):
    try:
        return await service.get_family_by_member_name(first_name, second_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 7. Получить количество пользователей
@router.get("/stats/count", response_model=int)
async def get_members_count(
    service: MembersService = Depends(get_members_service),
):
    return await service.get_members_count()


# 8. Получить количество семей
@router.get("/stats/families-count", response_model=int)
async def get_families_count(
    service: MembersService = Depends(get_members_service),
):
    return await service.get_families_count()


# 9. Получить участника по tg_username
@router.get("/tg_username", response_model=MemberRead)
async def get_member_by_tg_username(
    tg_username: str,
    service: MembersService = Depends(get_members_service),
):
    try:
        return await service.get_member_by_tg_username(tg_username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))



