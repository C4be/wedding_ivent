import logging
from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.wishes_repository import WishesRepository, get_wishes_repository
from schemas.wish_schema import WishCreate
from database.models import Wish


class WishesService:
    def __init__(self, repo: WishesRepository):
        self.repo = repo

    async def _resolve_member_id_by_tg(self, tg_username: str) -> int:
        logging.debug("Resolving member_id by tg_username=%s", tg_username)
        member = await self.repo.get_member_by_tg_username(tg_username)
        if member is None:
            logging.warning("Member not found by tg_username=%s", tg_username)
            raise ValueError(f"Member with tg_username='{tg_username}' not found")
        logging.debug("Resolved member_id=%s for tg_username=%s", member.id, tg_username)
        return member.id

    async def _resolve_member_id_by_name(self, first_name: str, second_name: str) -> int:
        logging.debug("Resolving member_id by name=%s %s", first_name, second_name)
        member = await self.repo.get_member_by_name(first_name, second_name)
        if member is None:
            logging.warning("Member not found by name=%s %s", first_name, second_name)
            raise ValueError(f"Member '{first_name} {second_name}' not found")
        logging.debug("Resolved member_id=%s for name=%s %s", member.id, first_name, second_name)
        return member.id

    async def _get_wish_or_raise(self, member_id: int) -> Wish:
        logging.debug("Fetching wish for member_id=%s", member_id)
        wish = await self.repo.get_wish_by_member_id(member_id)
        if wish is None:
            logging.warning("Wish not found for member_id=%s", member_id)
            raise ValueError(f"Wish for member_id={member_id} not found")
        logging.debug("Wish found: id=%s for member_id=%s", wish.id, member_id)
        return wish

    async def add_wish_by_tg_username(self, tg_username: str, data: WishCreate) -> Wish:
        logging.info("Adding wish for tg_username=%s", tg_username)
        member_id = await self._resolve_member_id_by_tg(tg_username)
        wish = await self.repo.add_wish(member_id, data)
        logging.info("Wish added: id=%s for member_id=%s", wish.id, member_id)
        return wish

    async def add_wish_by_name(self, first_name: str, second_name: str, data: WishCreate) -> Wish:
        logging.info("Adding wish for member name=%s %s", first_name, second_name)
        member_id = await self._resolve_member_id_by_name(first_name, second_name)
        wish = await self.repo.add_wish(member_id, data)
        logging.info("Wish added: id=%s for member_id=%s", wish.id, member_id)
        return wish

    async def delete_wish_by_tg_username(self, tg_username: str) -> bool:
        logging.info("Deleting wish for tg_username=%s", tg_username)
        member_id = await self._resolve_member_id_by_tg(tg_username)
        wish = await self._get_wish_or_raise(member_id)
        result = await self.repo.delete_wish(wish.id)
        logging.info("Wish deleted: id=%s for tg_username=%s", wish.id, tg_username)
        return result

    async def delete_wish_by_name(self, first_name: str, second_name: str) -> bool:
        logging.info("Deleting wish for member name=%s %s", first_name, second_name)
        member_id = await self._resolve_member_id_by_name(first_name, second_name)
        wish = await self._get_wish_or_raise(member_id)
        result = await self.repo.delete_wish(wish.id)
        logging.info("Wish deleted: id=%s for member name=%s %s", wish.id, first_name, second_name)
        return result

    async def add_drink(self, wish_id: int, drink: str) -> Wish:
        logging.info("Adding drink='%s' to wish_id=%s", drink, wish_id)
        wish = await self.repo.add_drink(wish_id, drink)
        if wish is None:
            logging.warning("Wish not found: id=%s", wish_id)
            raise ValueError(f"Wish with id={wish_id} not found")
        logging.info("Drink added to wish_id=%s, current drinks=%s", wish_id, wish.drinks)
        return wish

    async def remove_drink(self, wish_id: int, drink: str) -> Wish:
        logging.info("Removing drink='%s' from wish_id=%s", drink, wish_id)
        wish = await self.repo.remove_drink(wish_id, drink)
        if wish is None:
            logging.warning("Wish not found: id=%s", wish_id)
            raise ValueError(f"Wish with id={wish_id} not found")
        logging.info("Drink removed from wish_id=%s, current drinks=%s", wish_id, wish.drinks)
        return wish

    async def clear_drinks(self, wish_id: int) -> Wish:
        logging.info("Clearing all drinks for wish_id=%s", wish_id)
        wish = await self.repo.clear_drinks(wish_id)
        if wish is None:
            logging.warning("Wish not found: id=%s", wish_id)
            raise ValueError(f"Wish with id={wish_id} not found")
        logging.info("All drinks cleared for wish_id=%s", wish_id)
        return wish

    async def update_drinks(self, wish_id: int, drinks: List[str]) -> Wish:
        logging.info("Updating drinks for wish_id=%s, new drinks=%s", wish_id, drinks)
        wish = await self.repo.update_drinks(wish_id, drinks)
        if wish is None:
            logging.warning("Wish not found: id=%s", wish_id)
            raise ValueError(f"Wish with id={wish_id} not found")
        logging.info("Drinks updated for wish_id=%s, result=%s", wish_id, wish.drinks)
        return wish


async def get_wishes_service(
    repo: WishesRepository = Depends(get_wishes_repository),
) -> AsyncGenerator[WishesService, None]:
    yield WishesService(repo)
