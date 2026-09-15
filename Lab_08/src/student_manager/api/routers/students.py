"""/students resource: list with filters and pagination, read, create, partial update, delete, best."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from student_manager.api.dependencies import get_store
from student_manager.api.schemas import (
    ErrorOut, GroupCode, StudentCreate, StudentOut, StudentPage, StudentPatch,
)
from student_manager.api.store import SortKey, StudentStore

router = APIRouter(prefix="/students", tags=["students"])
Store = Annotated[StudentStore, Depends(get_store)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorOut, "description": "Студента не знайдено"}}


@router.get("", response_model=StudentPage, summary="Список студентів із пошуком, фільтром і пагінацією")
async def list_students(
    store: Store,
    last_name: Annotated[str | None, Query(min_length=1, description="Префікс прізвища, без урахування регістру")] = None,
    group: Annotated[GroupCode | None, Query(description="Лише студенти цієї групи")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: SortKey = "id",
) -> StudentPage:
    return await asyncio.to_thread(store.search, last_name=last_name, group=group, page=page, size=size, sort=sort)


@router.get("/best", response_model=StudentOut, responses=NOT_FOUND, summary="Студент із найбільшим середнім балом")
async def best_student(store: Store, group: GroupCode | None = None) -> StudentOut:
    best = await asyncio.to_thread(store.best, group)
    if best is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="немає жодного студента")
    return best


@router.get("/{student_id}", response_model=StudentOut, responses=NOT_FOUND)
async def get_student(store: Store, student_id: int) -> StudentOut:
    return await asyncio.to_thread(store.get, student_id)


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": ErrorOut, "description": "Порушення обмеження (наприклад, email зайнято)"}})
async def create_student(store: Store, data: StudentCreate) -> StudentOut:
    return await asyncio.to_thread(store.create, data)


@router.patch("/{student_id}", response_model=StudentOut, responses=NOT_FOUND,
              summary="Змінити бал, перевести до іншої групи або оновити email")
async def patch_student(store: Store, student_id: int, data: StudentPatch) -> StudentOut:
    if data.is_empty():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="тіло PATCH порожнє: немає що змінювати")
    return await asyncio.to_thread(store.patch, student_id, data)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def delete_student(store: Store, student_id: int) -> Response:
    if not await asyncio.to_thread(store.delete, student_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"студента з id={student_id} не знайдено")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
