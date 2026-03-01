from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from services.wishes_service import WishesService, get_wishes_service
from schemas.wish_schema import WishCreate, WishRead

router = APIRouter(prefix="/wishes", tags=["Wishes"])


# 1. Добавить желание по tg_username
@router.post("/by-tg/{tg_username}", response_model=WishRead, status_code=status.HTTP_201_CREATED)
async def add_wish_by_tg_username(
    tg_username: str,
    data: WishCreate,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.add_wish_by_tg_username(tg_username, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 2. Добавить желание по имени и фамилии
@router.post("/by-name", response_model=WishRead, status_code=status.HTTP_201_CREATED)
async def add_wish_by_name(
    first_name: str,
    second_name: str,
    data: WishCreate,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.add_wish_by_name(first_name, second_name, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 3. Удалить желание по tg_username
@router.delete("/by-tg/{tg_username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wish_by_tg_username(
    tg_username: str,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        await service.delete_wish_by_tg_username(tg_username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 4. Удалить желание по имени и фамилии
@router.delete("/by-name", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wish_by_name(
    first_name: str,
    second_name: str,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        await service.delete_wish_by_name(first_name, second_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 5a. Добавить один напиток
@router.patch("/{wish_id}/drinks/add", response_model=WishRead)
async def add_drink(
    wish_id: int,
    drink: str,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.add_drink(wish_id, drink)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 5b. Удалить один напиток
@router.patch("/{wish_id}/drinks/remove", response_model=WishRead)
async def remove_drink(
    wish_id: int,
    drink: str,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.remove_drink(wish_id, drink)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 5c. Удалить все напитки
@router.delete("/{wish_id}/drinks", response_model=WishRead)
async def clear_drinks(
    wish_id: int,
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.clear_drinks(wish_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 5d. Заменить список напитков целиком
@router.put("/{wish_id}/drinks", response_model=WishRead)
async def update_drinks(
    wish_id: int,
    drinks: List[str],
    service: WishesService = Depends(get_wishes_service),
):
    try:
        return await service.update_drinks(wish_id, drinks)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
