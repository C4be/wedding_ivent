from fastapi import Depends
from typing import AsyncGenerator
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Member
from database.db import get_async_session
from schemas.member_schema import MemberCreate



class MembersRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Member]:
        stmt = select(Member)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, member_id: int) -> Optional[Member]:
        stmt = select(Member).where(Member.id == member_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, data: MemberCreate) -> Member:
        obj = Member(**data.dict())
        self.db.add(obj)
        await self.db.flush()      # присвоит id
        await self.db.refresh(obj) # обновит объект из БД
        return obj

async def get_members_repository(
    db: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[MembersRepository, None]:
    yield MembersRepository(db)