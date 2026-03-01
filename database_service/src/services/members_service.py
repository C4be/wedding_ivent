from typing import AsyncGenerator, List
from fastapi import Depends
from repositories.members_repository import MembersRepository, get_members_repository
from schemas.member_schema import MemberCreate
from database.models import Member


class MembersService:
    def __init__(self, repo: MembersRepository):
        self.repo = repo

    async def get_all(self) -> List[Member]:
        return await self.repo.get_all()

    async def get_by_id(self, member_id: int) -> Member:
        return await self.repo.get_by_id(member_id)

    async def create(self, data: MemberCreate) -> Member:
        return await self.repo.create(data)


async def get_members_service(
    repo: MembersRepository = Depends(get_members_repository),
) -> AsyncGenerator[MembersService, None]:
    yield MembersService(repo)