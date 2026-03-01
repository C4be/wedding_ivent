from typing import AsyncGenerator, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_async_session
from database.models import Member, Wish
from repositories.members_repository import MembersRepository, get_members_repository
from schemas.wish_schema import WishCreate


class WishesRepository:
    def __init__(self, session: AsyncSession, members_repo: MembersRepository):
        self.session = session
        self.members_repo = members_repo

    # ── member helpers (delegated) ─────────────────────────────────────────────

    async def get_member_by_tg_username(self, tg_username: str) -> Optional[Member]:
        return await self.members_repo.get_member_by_tg_username(tg_username)

    async def get_member_by_name(self, first_name: str, second_name: str) -> Optional[Member]:
        return await self.members_repo.get_member_by_name(first_name, second_name)

    async def get_wish_by_member_id(self, member_id: int) -> Optional[Wish]:
        result = await self.session.execute(
            select(Wish).where(Wish.member_id == member_id)
        )
        return result.scalar_one_or_none()

    # 1. Добавить желание конкретному пользователю
    async def add_wish(self, member_id: int, data: WishCreate) -> Wish:
        member = await self.session.get(Member, member_id)
        if member is None:
            raise ValueError(f"Member with id={member_id} not found")

        existing = await self.session.execute(
            select(Wish).where(Wish.member_id == member_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Member with id={member_id} already has a wish")

        wish = Wish(
            member_id=member_id,
            wish_text=data.wish_text,
            drinks=data.drinks,
        )
        self.session.add(wish)
        await self.session.commit()
        await self.session.refresh(wish)
        return wish

    # 2. Удалить желание по id
    async def delete_wish(self, wish_id: int) -> bool:
        wish = await self.session.get(Wish, wish_id)
        if wish is None:
            return False
        await self.session.delete(wish)
        await self.session.commit()
        return True

    # 3а. Добавить напиток в список
    async def add_drink(self, wish_id: int, drink: str) -> Optional[Wish]:
        wish = await self.session.get(Wish, wish_id)
        if wish is None:
            return None
        current: List[str] = list(wish.drinks or [])
        drink = drink.strip()
        if not drink:
            raise ValueError("drink must be a non-empty string")
        if drink not in current:
            current.append(drink)
            wish.drinks = current
            await self.session.commit()
            await self.session.refresh(wish)
        return wish

    # 3б. Убрать напиток из списка
    async def remove_drink(self, wish_id: int, drink: str) -> Optional[Wish]:
        wish = await self.session.get(Wish, wish_id)
        if wish is None:
            return None
        current: List[str] = list(wish.drinks or [])
        drink = drink.strip()
        if drink not in current:
            raise ValueError(f"Drink '{drink}' not found in the wish list")
        current.remove(drink)
        wish.drinks = current or None
        await self.session.commit()
        await self.session.refresh(wish)
        return wish

    # 4. Удалить все напитки
    async def clear_drinks(self, wish_id: int) -> Optional[Wish]:
        wish = await self.session.get(Wish, wish_id)
        if wish is None:
            return None
        wish.drinks = None
        await self.session.commit()
        await self.session.refresh(wish)
        return wish

    # 5. Обновить список напитков целиком
    async def update_drinks(self, wish_id: int, drinks: List[str]) -> Optional[Wish]:
        wish = await self.session.get(Wish, wish_id)
        if wish is None:
            return None
        cleaned = [d.strip() for d in drinks if d.strip()]
        wish.drinks = cleaned or None
        await self.session.commit()
        await self.session.refresh(wish)
        return wish


async def get_wishes_repository(
    db: AsyncSession = Depends(get_async_session),
    members_repo: MembersRepository = Depends(get_members_repository),
) -> AsyncGenerator[WishesRepository, None]:
    yield WishesRepository(db, members_repo)