from fastapi import Depends
from typing import AsyncGenerator
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Member
from database.db import get_async_session
from schemas.member_schema import MemberCreate


class MembersRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 1. Добавить одного пользователя
    async def add_member(self, data: MemberCreate) -> Member:
        member = Member(**data.model_dump())
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    # 2. Добавить несколько пользователей (один из них is_main_account=True)
    async def add_members(self, members_data: list[MemberCreate]) -> list[Member]:
        # Сначала находим главного
        head_data = next((m for m in members_data if m.is_main_account), None)

        if head_data is None:
            raise ValueError("At least one member must have is_main_account=True")

        # Сохраняем главного, чтобы получить его id
        head = Member(**head_data.model_dump())
        self.session.add(head)
        await self.session.flush()  # получаем head.id без коммита

        # Сохраняем остальных, проставляя main_account = head.id
        children: list[Member] = []
        for m_data in members_data:
            if m_data.is_main_account:
                continue
            child = Member(**m_data.model_dump())
            child.main_account = head.id
            self.session.add(child)
            children.append(child)

        await self.session.commit()
        await self.session.refresh(head)
        for child in children:
            await self.session.refresh(child)

        return [head, *children]

    # 3. Удалить пользователя по id
    async def delete_member(self, member_id: int) -> bool:
        member = await self.session.get(Member, member_id)
        if member is None:
            return False
        await self.session.delete(member)
        await self.session.commit()
        return True

    # 4а. Добавить номер телефона пользователю
    async def update_phone_number(self, member_id: int, phone_number: str) -> Optional[Member]:
        member = await self.session.get(Member, member_id)
        if member is None:
            return None
        member.phone_number = phone_number
        await self.session.commit()
        await self.session.refresh(member)
        return member

    # 4б. Обновить is_going_on_event у пользователя
    async def update_going_on_event(self, member_id: int, is_going: bool) -> Optional[Member]:
        member = await self.session.get(Member, member_id)
        if member is None:
            return None
        member.is_going_on_event = is_going
        await self.session.commit()
        await self.session.refresh(member)
        return member

    # 5. Получить список всех пользователей
    async def get_all_members(self) -> list[Member]:
        result = await self.session.execute(select(Member))
        return list(result.scalars().all())

    # 6. Получить группу (семью) по имени и фамилии любого участника
    async def get_family_by_member_name(
        self, first_name: str, second_name: str
    ) -> list[Member]:
        # Ищем участника по имени и фамилии
        stmt = select(Member).where(
            Member.first_name == first_name,
            Member.second_name == second_name,
        )
        result = await self.session.execute(stmt)
        found: list[Member] = list(result.scalars().all())

        if not found:
            return []

        family_ids: set[int] = set()
        for member in found:
            if member.is_main_account:
                # найден глава — берём его и всех его детей
                family_ids.add(member.id)
                children_stmt = select(Member).where(Member.main_account == member.id)
                children_result = await self.session.execute(children_stmt)
                family_ids.update(m.id for m in children_result.scalars().all())
            else:
                # найден дочерний — берём главу и всех детей главы
                head_id = member.main_account
                if head_id is None:
                    # одиночный участник без семьи
                    family_ids.add(member.id)
                else:
                    family_ids.add(head_id)
                    siblings_stmt = select(Member).where(
                        or_(
                            Member.id == head_id,
                            Member.main_account == head_id,
                        )
                    )
                    siblings_result = await self.session.execute(siblings_stmt)
                    family_ids.update(m.id for m in siblings_result.scalars().all())

        family_stmt = select(Member).where(Member.id.in_(family_ids))
        family_result = await self.session.execute(family_stmt)
        return list(family_result.scalars().all())

    # 7. Получить количество пользователей
    async def get_members_count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Member))
        return result.scalar_one()

    # 8. Получить количество семей (участники, у которых main_account IS NULL)
    async def get_families_count(self) -> int:
        stmt = select(func.count()).select_from(Member).where(
            Member.main_account.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # helper: найти участника по tg_username
    async def get_member_by_tg_username(self, tg_username: str) -> Optional[Member]:
        result = await self.session.execute(
            select(Member).where(Member.tg_username == tg_username)
        )
        return result.scalar_one_or_none()

    # helper: найти участника по имени и фамилии
    async def get_member_by_name(self, first_name: str, second_name: str) -> Optional[Member]:
        result = await self.session.execute(
            select(Member).where(
                Member.first_name == first_name,
                Member.second_name == second_name,
            )
        )
        return result.scalars().first()

async def get_members_repository(
    db: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[MembersRepository, None]:
    yield MembersRepository(db)