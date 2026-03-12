import logging
from typing import AsyncGenerator, List
from fastapi import Depends
from repositories.members_repository import MembersRepository, get_members_repository
from schemas.member_schema import MemberCreate
from database.models import Member


class MembersService:
    def __init__(self, repo: MembersRepository):
        self.repo = repo

    async def add_member(self, data: MemberCreate) -> Member:
        logging.info("Adding member: first_name=%s, second_name=%s", data.first_name, data.second_name)
        member = await self.repo.add_member(data)
        logging.info("Member added successfully: id=%s", member.id)
        return member

    async def add_members(self, members_data: List[MemberCreate]) -> List[Member]:
        logging.info("Adding family of %d members", len(members_data))
        if not members_data:
            logging.warning("add_members called with empty list")
            raise ValueError("members_data cannot be empty")
        heads = [m for m in members_data if m.is_main_account]
        if len(heads) != 1:
            logging.warning("add_members: expected 1 head, got %d", len(heads))
            raise ValueError("Exactly one member must have is_main_account=True")
        members = await self.repo.add_members(members_data)
        logging.info("Family added successfully: ids=%s", [m.id for m in members])
        return members

    async def delete_member(self, member_id: int) -> bool:
        logging.info("Deleting member: id=%s", member_id)
        deleted = await self.repo.delete_member(member_id)
        if not deleted:
            logging.warning("Member not found for deletion: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("Member deleted successfully: id=%s", member_id)
        return True

    async def update_phone_number(self, member_id: int, phone_number: str) -> Member:
        logging.info("Updating phone_number for member id=%s", member_id)
        member = await self.repo.update_phone_number(member_id, phone_number)
        if member is None:
            logging.warning("Member not found for phone update: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("Phone number updated for member id=%s", member_id)
        return member

    async def update_going_on_event(self, member_id: int, is_going: bool) -> Member:
        logging.info("Updating is_going_on_event=%s for member id=%s", is_going, member_id)
        member = await self.repo.update_going_on_event(member_id, is_going)
        if member is None:
            logging.warning("Member not found for going update: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("is_going_on_event updated for member id=%s", member_id)
        return member

    async def update_telegram_id(self, member_id: int, telegram_id: int) -> Member:
        logging.info("Updating telegram_id=%s for member id=%s", telegram_id, member_id)
        member = await self.repo.update_telegram_id(member_id, telegram_id)
        if member is None:
            logging.warning("Member not found for telegram_id update: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("telegram_id updated for member id=%s", member_id)
        return member

    async def update_chat_id(self, member_id: int, chat_id: int) -> Member:
        logging.info("Updating chat_id=%s for member id=%s", chat_id, member_id)
        member = await self.repo.update_chat_id(member_id, chat_id)
        if member is None:
            logging.warning("Member not found for chat_id update: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("chat_id updated for member id=%s", member_id)
        return member

    async def update_tg_username(self, member_id: int, tg_username: str) -> Member:
        logging.info("Updating tg_username=%s for member id=%s", tg_username, member_id)
        member = await self.repo.update_tg_username(member_id, tg_username)
        if member is None:
            logging.warning("Member not found for tg_username update: id=%s", member_id)
            raise ValueError(f"Member with id={member_id} not found")
        logging.info("tg_username updated for member id=%s", member_id)
        return member

    async def get_all_members(self) -> List[Member]:
        logging.info("Fetching all members")
        members = await self.repo.get_all_members()
        logging.info("Fetched %d members", len(members))
        return members

    async def get_family_by_member_name(self, first_name: str, second_name: str) -> List[Member]:
        logging.info("Fetching family by name: %s %s", first_name, second_name)
        family = await self.repo.get_family_by_member_name(first_name, second_name)
        if not family:
            logging.warning("No family found for name: %s %s", first_name, second_name)
            raise ValueError(f"No members found with name '{first_name} {second_name}'")
        logging.info("Found %d family members for %s %s", len(family), first_name, second_name)
        return family

    async def get_members_count(self) -> int:
        logging.info("Fetching members count")
        count = await self.repo.get_members_count()
        logging.info("Members count: %d", count)
        return count

    async def get_families_count(self) -> int:
        logging.info("Fetching families count")
        count = await self.repo.get_families_count()
        logging.info("Families count: %d", count)
        return count

    async def get_member_by_tg_username(self, tg_username: str) -> Member:
        logging.info("Fetching member by tg_username=%s", tg_username)
        member = await self.repo.get_member_by_tg_username(tg_username)
        if member is None:
            logging.warning("Member not found by tg_username=%s", tg_username)
            raise ValueError(f"Member with tg_username='{tg_username}' not found")
        logging.info("Member found: id=%s, tg_username=%s", member.id, tg_username)
        return member

    async def get_member_by_telegram_id(self, telegram_id: int) -> Member:
        logging.info("Fetching member by telegram_id=%s", telegram_id)
        member = await self.repo.get_member_by_telegram_id(telegram_id)
        if member is None:
            logging.warning("Member not found by telegram_id=%s", telegram_id)
            raise ValueError(f"Member with telegram_id={telegram_id} not found")
        logging.info("Member found: id=%s, telegram_id=%s", member.id, telegram_id)
        return member

    async def get_member_by_chat_id(self, chat_id: int) -> Member:
        logging.info("Fetching member by chat_id=%s", chat_id)
        member = await self.repo.get_member_by_chat_id(chat_id)
        if member is None:
            logging.warning("Member not found by chat_id=%s", chat_id)
            raise ValueError(f"Member with chat_id={chat_id} not found")
        logging.info("Member found: id=%s, chat_id=%s", member.id, chat_id)
        return member

    async def get_member_by_phone_number(self, phone_number: str) -> Member:
        logging.info("Fetching member by phone_number=%s", phone_number)
        member = await self.repo.get_member_by_phone_number(phone_number)
        if member is None:
            logging.warning("Member not found by phone_number=%s", phone_number)
            raise ValueError(f"Member with phone_number='{phone_number}' not found")
        logging.info("Member found: id=%s, phone_number=%s", member.id, phone_number)
        return member

    async def get_member_by_name(self, first_name: str, second_name: str) -> Member:
        logging.info("Fetching member by name=%s %s", first_name, second_name)
        member = await self.repo.get_member_by_name(first_name, second_name)
        if member is None:
            logging.warning("Member not found by name=%s %s", first_name, second_name)
            raise ValueError(f"Member with name='{first_name} {second_name}' not found")
        logging.info("Member found: id=%s, name=%s %s", member.id, first_name, second_name)
        return member


async def get_members_service(
    repo: MembersRepository = Depends(get_members_repository),
) -> AsyncGenerator[MembersService, None]:
    yield MembersService(repo)