"""/groups resource: statistics of one, several (concurrently) or all groups, and the students of a group."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from student_manager.api.concurrency import gather_statistics
from student_manager.api.dependencies import get_store
from student_manager.api.schemas import ErrorOut, GroupCode, GroupStatisticsOut, StudentOut
from student_manager.api.store import StudentStore

router = APIRouter(prefix="/groups", tags=["groups"])
Store = Annotated[StudentStore, Depends(get_store)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorOut, "description": "Групи не знайдено"}}


@router.get("", response_model=list[GroupStatisticsOut], summary="Усі групи зі статистикою")
async def list_groups(store: Store) -> list[GroupStatisticsOut]:
    return await asyncio.to_thread(store.groups)


@router.get(
    "/statistics",
    response_model=list[GroupStatisticsOut],
    responses=NOT_FOUND,
    summary="Статистика кількох груп одночасно (Task + gather + Semaphore)",
)
async def statistics_many(
    store: Store,
    code: Annotated[list[GroupCode], Query(min_length=1, description="Повторюваний параметр: ?code=A&code=B")],
    limit: Annotated[int, Query(ge=1, le=10, description="Скільки груп рахувати паралельно")] = 3,
) -> list[GroupStatisticsOut]:
    return await gather_statistics(store, code, limit=limit)


@router.get("/{code}/students", response_model=list[StudentOut], responses=NOT_FOUND)
async def group_students(store: Store, code: GroupCode) -> list[StudentOut]:
    return await asyncio.to_thread(store.group_students, code)


@router.get("/{code}/statistics", response_model=GroupStatisticsOut, responses=NOT_FOUND)
async def group_statistics(store: Store, code: GroupCode) -> GroupStatisticsOut:
    return await asyncio.to_thread(store.group_statistics, code)
