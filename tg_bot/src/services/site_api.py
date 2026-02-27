import aiohttp
from typing import Any, Optional
from src.config import SITE_API_URL, SITE_API_KEY
from src.utils.logger import logger


HEADERS = {"X-API-Key": SITE_API_KEY, "Content-Type": "application/json"}


async def _request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Optional[Any]:
    url = f"{SITE_API_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.request(
                method, url, json=data, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"Site API {method} {url} returned {resp.status}")
                return None
    except Exception as e:
        logger.error(f"Site API request error: {e}")
        return None


async def get_site_config() -> Optional[dict]:
    return await _request("GET", "/api/config")


async def update_site_config(config: dict) -> Optional[dict]:
    return await _request("POST", "/api/config", data=config)


async def get_members_from_site() -> Optional[list]:
    return await _request("GET", "/api/members")


async def add_member_to_site(member: dict) -> Optional[dict]:
    return await _request("POST", "/api/members", data=member)


async def delete_member_from_site(member_id: int) -> Optional[dict]:
    return await _request("DELETE", f"/api/members/{member_id}")


async def add_image_to_site(image_data: dict) -> Optional[dict]:
    return await _request("POST", "/api/gallery", data=image_data)
