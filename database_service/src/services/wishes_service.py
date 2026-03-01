from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.wishes_repository import WishesRepository, get_wishes_repository
from schemas.wish_schema import WishCreate
from database.models import Wish


class WishesService:
    def __init__(self, repo: WishesRepository):
        self.repo = repo

    # ── internal helpers ───────────────────────────────────────────────────────

    async def _resolve_member_id_by_tg(self, tg_username: str) -> int:
        member = await self.repo.get_member_by_tg_username(tg_username)
        if member is None:
            raise ValueError(f"Member with tg_username='{tg_username}' not found")
        return member.id

    async def _resolve_member_id_by_name(self, first_name: str, second_name: str) -> int:
        member = await self.repo.get_member_by_name(first_name, second_name)
        if member is None:
            raise ValueError(f"Member '{first_name} {second_name}' not found")
        return member.id

    async def _get_wish_or_raise(self, member_id: int) -> Wish:
        wish = await self.repo.get_wish_by_member_id(member_id)
        if wish is None:
            raise ValueError(f"Wish for member_id={member_id} not found")
        return wish

    # 1. Добавить желание по tg_username
    async def add_wish_by_tg_username(self, tg_username: str, data: WishCreate) -> Wish:
        member_id = await self._resolve_member_id_by_tg(tg_username)
        return await self.repo.add_wish(member_id, data)

    # 2. Добавить желание по имени и фамилии
    async def add_wish_by_name(
        self, first_name: str, second_name: str, data: WishCreate
    ) -> Wish:
        member_id = await self._resolve_member_id_by_name(first_name, second_name)
        return await self.repo.add_wish(member_id, data)

    # 3. Удалить желание по tg_username
    async def delete_wish_by_tg_username(self, tg_username: str) -> bool:
        member_id = await self._resolve_member_id_by_tg(tg_username)
        wish = await self._get_wish_or_raise(member_id)
        return await self.repo.delete_wish(wish.id)

    # 4. Удалить желание по имени и фамилии
    async def delete_wish_by_name(self, first_name: str, second_name: str) -> bool:
        member_id = await self._resolve_member_id_by_name(first_name, second_name)
        wish = await self._get_wish_or_raise(member_id)
        return await self.repo.delete_wish(wish.id)

    # 5a. Добавить один напиток (по wish_id)
    async def add_drink(self, wish_id: int, drink: str) -> Wish:
        wish = await self.repo.add_drink(wish_id, drink)
        if wish is None:
            raise ValueError(f"Wish with id={wish_id} not found")
        return wish

    # 5b. Удалить один напиток (по wish_id)
    async def remove_drink(self, wish_id: int, drink: str) -> Wish:
        wish = await self.repo.remove_drink(wish_id, drink)
        if wish is None:
            raise ValueError(f"Wish with id={wish_id} not found")
        return wish

    # 5c. Удалить все напитки (по wish_id)
    async def clear_drinks(self, wish_id: int) -> Wish:
        wish = await self.repo.clear_drinks(wish_id)
        if wish is None:
            raise ValueError(f"Wish with id={wish_id} not found")
        return wish

    # 5d. Заменить список напитков целиком (по wish_id)
    async def update_drinks(self, wish_id: int, drinks: List[str]) -> Wish:
        wish = await self.repo.update_drinks(wish_id, drinks)
        if wish is None:
            raise ValueError(f"Wish with id={wish_id} not found")
        return wish


async def get_wishes_service(
    repo: WishesRepository = Depends(get_wishes_repository),
) -> AsyncGenerator[WishesService, None]:
    yield WishesService(repo)
