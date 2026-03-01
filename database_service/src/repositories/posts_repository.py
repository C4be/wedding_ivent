from typing import AsyncGenerator, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_async_session
from database.models import PreparedPost
from schemas.post_schema import PreparedPostCreate, PreparedPostUpdate


class PostsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 1. Создать пост
    async def create_post(self, data: PreparedPostCreate) -> PreparedPost:
        post = PreparedPost(**data.model_dump())
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    # 2. Получить пост по id
    async def get_post(self, post_id: int) -> Optional[PreparedPost]:
        return await self.session.get(PreparedPost, post_id)

    # 3. Получить все посты
    async def get_all_posts(self) -> List[PreparedPost]:
        result = await self.session.execute(select(PreparedPost))
        return list(result.scalars().all())

    # 4. Обновить пост
    async def update_post(self, post_id: int, data: PreparedPostUpdate) -> Optional[PreparedPost]:
        post = await self.session.get(PreparedPost, post_id)
        if post is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(post, field, value)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    # 5. Удалить пост
    async def delete_post(self, post_id: int) -> bool:
        post = await self.session.get(PreparedPost, post_id)
        if post is None:
            return False
        await self.session.delete(post)
        await self.session.commit()
        return True


async def get_posts_repository(
    db: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[PostsRepository, None]:
    yield PostsRepository(db)
