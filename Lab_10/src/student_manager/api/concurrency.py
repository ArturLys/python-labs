"""asyncio building blocks used by the API and the client: tasks + gather, timeout, semaphore, retry with backoff."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Protocol, TypeVar

from student_manager.api.schemas import GroupStatisticsOut

T = TypeVar("T")
logger = logging.getLogger(__name__)


class StatisticsSource(Protocol):
    def group_statistics(self, code: str) -> GroupStatisticsOut: ...


async def gather_statistics(
    source: StatisticsSource, codes: Iterable[str], *, limit: int = 3, timeout: float = 2.0
) -> list[GroupStatisticsOut]:
    """Statistics of several groups at once.

    One Task per group; the Semaphore lets at most ``limit`` of them touch the database simultaneously; each
    database call runs in a worker thread (the SQLAlchemy session is synchronous) under its own timeout.
    ``gather`` keeps the order of ``codes`` and propagates the first exception.
    """
    semaphore = asyncio.Semaphore(limit)

    async def one(code: str) -> GroupStatisticsOut:
        async with semaphore:
            async with asyncio.timeout(timeout):
                return await asyncio.to_thread(source.group_statistics, code)

    tasks = [asyncio.create_task(one(code), name=f"statistics:{code}") for code in codes]
    return list(await asyncio.gather(*tasks))


async def retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    label: str = "operation",
) -> T:
    """Call ``operation`` up to ``attempts`` times; wait base_delay * 2**(n-1) between attempts (exponential backoff)."""
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retry_on as error:
            reason = f"{type(error).__name__}: {error}" if str(error) else type(error).__name__
            if attempt == attempts:
                logger.warning("%s: спроба %d/%d невдала (%s) — здаюся", label, attempt, attempts, reason)
                raise
            delay = base_delay * 2 ** (attempt - 1)
            logger.warning(
                "%s: спроба %d/%d невдала (%s), повтор через %.2f с", label, attempt, attempts, reason, delay
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")
