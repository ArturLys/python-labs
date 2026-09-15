"""Asynchronous HTTP client for the Student Manager API built on httpx.AsyncClient.

One client instance owns one connection pool (lifecycle via ``async with``), a configurable timeout, a retry
budget with exponential backoff, and a Semaphore that caps how many requests are in flight at once.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from student_manager.api.concurrency import retry

RETRYABLE_STATUSES = frozenset({502, 503, 504})


class RetryableStatusError(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"HTTP {response.status_code} {response.request.method} {response.request.url.path}")
        self.response = response


class StudentApiClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 5.0,
        attempts: int = 3,
        base_delay: float = 0.2,
        concurrency: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)
        self._attempts = attempts
        self._base_delay = base_delay
        self._semaphore = asyncio.Semaphore(concurrency)

    async def __aenter__(self) -> StudentApiClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._client.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Semaphore -> retry(timeouts, connection errors, 502/503/504) -> raise for other 4xx/5xx."""

        async def once() -> httpx.Response:
            async with self._semaphore:
                response = await self._client.request(method, path, **kwargs)
            if response.status_code in RETRYABLE_STATUSES:
                raise RetryableStatusError(response)
            return response

        response = await retry(
            once,
            attempts=self._attempts,
            base_delay=self._base_delay,
            retry_on=(httpx.TransportError, RetryableStatusError),
            label=f"{method} {path}",
        )
        response.raise_for_status()
        return response

    async def get_json(self, path: str, **params: Any) -> Any:
        return (await self.request("GET", path, params=params)).json()

    async def create_student(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = (await self.request("POST", "/students", json=payload)).json()
        return data

    async def statistics(self, code: str) -> dict[str, Any]:
        data: dict[str, Any] = await self.get_json(f"/groups/{code}/statistics")
        return data

    async def statistics_many(self, codes: list[str]) -> list[dict[str, Any]]:
        """Parallel HTTP requests: one Task per group, gathered; the Semaphore in request() limits concurrency."""
        tasks = [asyncio.create_task(self.statistics(code)) for code in codes]
        return list(await asyncio.gather(*tasks))
