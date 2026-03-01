from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.posts_repository import PostsRepository, get_posts_repository
from schemas.post_schema import PreparedPostCreate, PreparedPostUpdate
from database.models import PreparedPost


class PostsService:
    def __init__(self, repo: PostsRepository):
        self.repo = repo

    # 1. Создать пост
    async def create_post(self, data: PreparedPostCreate) -> PreparedPost:
        return await self.repo.create_post(data)

    # 2. Получить пост по id
    async def get_post(self, post_id: int) -> PreparedPost:
        post = await self.repo.get_post(post_id)
        if post is None:
            raise ValueError(f"Post with id={post_id} not found")
        return post

    # 3. Получить все посты
    async def get_all_posts(self) -> List[PreparedPost]:
        return await self.repo.get_all_posts()

    # 4. Обновить пост
    async def update_post(self, post_id: int, data: PreparedPostUpdate) -> PreparedPost:
        post = await self.repo.update_post(post_id, data)
        if post is None:
            raise ValueError(f"Post with id={post_id} not found")
        return post

    # 5. Удалить пост
    async def delete_post(self, post_id: int) -> bool:
        deleted = await self.repo.delete_post(post_id)
        if not deleted:
            raise ValueError(f"Post with id={post_id} not found")
        return True


async def get_posts_service(
    repo: PostsRepository = Depends(get_posts_repository),
) -> AsyncGenerator[PostsService, None]:
    yield PostsService(repo)
