# ...existing code...
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Union

import httpx


JSON = Union[Dict[str, Any], list, str, int, float, bool, None]


class AsyncHTTPClient:
    """
    Лёгкая оболочка над httpx.AsyncClient.
    Поддерживает get/post/put/patch и общую request с опциями:
      - json / data / params / headers / timeout
      - retries (количество повторов при ошибке сетевого уровня или 5xx)
      - backoff (начальная задержка в секундах, экспоненциальный рост)

    Пример использования:

    async def main():
        async with AsyncHTTPClient(base_url="https://example.com") as client:
            # Пример POST с передачей данных через JSON
            response = await client.post(
                "/api/resource",
                json={"key": "value", "another_key": 123},
            )
            print(response.json())

            # Пример POST с передачей данных через form-urlencoded
            response = await client.post(
                "/api/resource",
                data={"key": "value", "another_key": 123},
            )
            print(response.text())

            # Пример POST с передачей параметров через query string
            response = await client.post(
                "/api/resource",
                params={"key": "value", "another_key": 123},
            )
            print(response.status_code)

    asyncio.run(main())
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        trust_env: bool = False,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url or "", headers=headers or {}, timeout=timeout, trust_env=trust_env)

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[JSON] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        retries: int = 0,
        backoff: float = 0.5,
    ) -> httpx.Response:
        attempt = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                resp = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                )
                # пробрасываем 4xx/5xx как исключение, чтобы можно было ретраить по 5xx
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # retry only on 5xx server errors
                if 500 <= status < 600 and attempt < retries:
                    last_exc = exc
                else:
                    raise
            except (httpx.TransportError, httpx.RequestError) as exc:
                last_exc = exc
            attempt += 1
            if attempt > retries:
                # если исчерпаны попытки — пробросим последнее исключение
                raise last_exc or RuntimeError("Unknown httpx error")
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()