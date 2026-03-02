from typing import AsyncGenerator, List
from fastapi import Depends
from repositories.members_repository import MembersRepository, get_members_repository
from schemas.member_schema import MemberCreate
from database.models import Member


class MembersService:
    def __init__(self, repo: MembersRepository):
        self.repo = repo

    # 1. Добавить одного пользователя
    async def add_member(self, data: MemberCreate) -> Member:
        return await self.repo.add_member(data)

    # 2. Добавить нескольких пользователей (семью)
    async def add_members(self, members_data: List[MemberCreate]) -> List[Member]:
        if not members_data:
            raise ValueError("members_data cannot be empty")
        heads = [m for m in members_data if m.is_main_account]
        if len(heads) != 1:
            raise ValueError("Exactly one member must have is_main_account=True")
        return await self.repo.add_members(members_data)

    # 3. Удалить пользователя по id
    async def delete_member(self, member_id: int) -> bool:
        deleted = await self.repo.delete_member(member_id)
        if not deleted:
            raise ValueError(f"Member with id={member_id} not found")
        return True

    # 4а. Обновить номер телефона
    async def update_phone_number(self, member_id: int, phone_number: str) -> Member:
        member = await self.repo.update_phone_number(member_id, phone_number)
        if member is None:
            raise ValueError(f"Member with id={member_id} not found")
        return member

    # 4б. Обновить статус присутствия на свадьбе
    async def update_going_on_event(self, member_id: int, is_going: bool) -> Member:
        member = await self.repo.update_going_on_event(member_id, is_going)
        if member is None:
            raise ValueError(f"Member with id={member_id} not found")
        return member

    # 5. Получить список всех пользователей
    async def get_all_members(self) -> List[Member]:
        return await self.repo.get_all_members()

    # 6. Получить группу (семью) по имени и фамилии любого участника
    async def get_family_by_member_name(
        self, first_name: str, second_name: str
    ) -> List[Member]:
        family = await self.repo.get_family_by_member_name(first_name, second_name)
        if not family:
            raise ValueError(
                f"No members found with name '{first_name} {second_name}'"
            )
        return family

    # 7. Получить количество пользователей
    async def get_members_count(self) -> int:
        return await self.repo.get_members_count()

    # 8. Получить количество семей
    async def get_families_count(self) -> int:
        return await self.repo.get_families_count()

    # 9. Получить участника по tg_username
    async def get_member_by_tg_username(self, tg_username: str) -> Member:
        member = await self.repo.get_member_by_tg_username(tg_username)
        if member is None:
            raise ValueError(f"Member with tg_username='{tg_username}' not found")
        return member


async def get_members_service(
    repo: MembersRepository = Depends(get_members_repository),
) -> AsyncGenerator[MembersService, None]:
    yield MembersService(repo)