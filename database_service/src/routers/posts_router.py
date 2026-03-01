from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from services.posts_service import PostsService, get_posts_service
from schemas.post_schema import PreparedPostCreate, PreparedPostRead, PreparedPostUpdate

router = APIRouter(prefix="/posts", tags=["Posts"])


# 1. Создать пост
@router.post("/", response_model=PreparedPostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PreparedPostCreate,
    service: PostsService = Depends(get_posts_service),
):
    return await service.create_post(data)


# 2. Получить пост по id
@router.get("/{post_id}", response_model=PreparedPostRead)
async def get_post(
    post_id: int,
    service: PostsService = Depends(get_posts_service),
):
    try:
        return await service.get_post(post_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 3. Получить все посты
@router.get("/", response_model=List[PreparedPostRead])
async def get_all_posts(
    service: PostsService = Depends(get_posts_service),
):
    return await service.get_all_posts()


# 4. Обновить пост
@router.patch("/{post_id}", response_model=PreparedPostRead)
async def update_post(
    post_id: int,
    data: PreparedPostUpdate,
    service: PostsService = Depends(get_posts_service),
):
    try:
        return await service.update_post(post_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# 5. Удалить пост
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    service: PostsService = Depends(get_posts_service),
):
    try:
        await service.delete_post(post_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
