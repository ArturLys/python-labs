"""FastAPI application factory: lifespan (engine, store, outbound HTTP client), routers, exception handlers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from student_manager.api.routers import debug, groups, students
from student_manager.api.schemas import ErrorOut
from student_manager.api.store import StudentStore
from student_manager.db import (
    DEFAULT_URL, ConstraintViolationError, RecordNotFoundError, create_schema, make_engine, make_session_factory,
)
from student_manager.exceptions import StudentManagerError

DESCRIPTION = """Асинхронний REST API системи обліку студентів (лабораторна робота №8).

Ресурси: **students** і **groups**. Дані зберігаються в SQLite через persistence layer ЛР7."""

TAGS = [
    {"name": "students", "description": "CRUD, пошук за прізвищем, фільтр за групою, найкращий студент"},
    {"name": "groups", "description": "Статистика груп; кілька груп одночасно через asyncio.gather"},
    {"name": "debug", "description": "Повільні та нестабільні endpoint-и для демонстрації timeout і retry"},
]


def create_app(*, database_url: str = DEFAULT_URL, include_debug: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(database_url)
        create_schema(engine)  # no-op on a database already built by `alembic upgrade head`
        app.state.store = StudentStore(make_session_factory(engine))
        app.state.http = httpx.AsyncClient(timeout=5.0)  # one outbound client for the whole app lifetime
        app.state.flaky_calls = 0
        try:
            yield
        finally:
            await app.state.http.aclose()
            engine.dispose()

    app = FastAPI(title="Student Manager API", version="0.8.0", description=DESCRIPTION, openapi_tags=TAGS,
                  lifespan=lifespan, contact={"name": "Артур Лис", "email": "Artur.Lys@lnu.edu.ua"})
    app.include_router(students.router)
    app.include_router(groups.router)
    if include_debug:
        app.include_router(debug.router)
    register_exception_handlers(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Domain exceptions -> structured JSON errors with the right status code; no traceback leaks to the client."""

    def error(status_code: int, code: str, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content=ErrorOut(error=code, detail=str(exc)).model_dump())

    @app.exception_handler(RecordNotFoundError)
    async def not_found(_: Request, exc: RecordNotFoundError) -> JSONResponse:
        return error(404, "not_found", exc)

    @app.exception_handler(ConstraintViolationError)
    async def conflict(_: Request, exc: ConstraintViolationError) -> JSONResponse:
        return error(409, "conflict", exc)

    @app.exception_handler(StudentManagerError)
    async def bad_request(_: Request, exc: StudentManagerError) -> JSONResponse:
        return error(400, "bad_request", exc)
