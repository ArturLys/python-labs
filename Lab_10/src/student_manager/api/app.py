"""FastAPI application factory: settings, lifespan (engine, store, outbound HTTP client), routers, /health,
exception handlers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from student_manager import __version__
from student_manager.api.routers import debug, groups, students
from student_manager.api.schemas import ErrorOut, HealthOut
from student_manager.api.store import StudentStore
from student_manager.db import (
    ConstraintViolationError,
    RecordNotFoundError,
    create_schema,
    make_engine,
    make_session_factory,
)
from student_manager.exceptions import StudentManagerError
from student_manager.settings import Settings, configure_logging

DESCRIPTION = """Асинхронний REST API системи обліку студентів (лабораторні роботи №8 і №10).

Ресурси: **students** і **groups**. Дані зберігаються в базі з `DATABASE_URL` через persistence layer ЛР7.
Коли задано `API_TOKEN`, запити POST/PATCH/DELETE потребують заголовка `X-API-Token`."""

TAGS = [
    {"name": "students", "description": "CRUD, пошук за прізвищем, фільтр за групою, найкращий студент"},
    {"name": "groups", "description": "Статистика груп; кілька груп одночасно через asyncio.gather"},
    {"name": "ops", "description": "Службові endpoint-и: перевірка живості для Docker/CI"},
    {"name": "debug", "description": "Повільні та нестабільні endpoint-и для демонстрації timeout і retry"},
]
logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None, *, database_url: str | None = None, include_debug: bool = False
) -> FastAPI:
    settings = settings if settings is not None else Settings.from_env()
    url = database_url if database_url is not None else settings.database_url

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logger.info("start: version=%s settings=%s", __version__, settings.redacted())
        engine = make_engine(url)
        create_schema(engine)  # no-op on a database already built by `alembic upgrade head`
        app.state.settings = settings
        app.state.store = StudentStore(make_session_factory(engine))
        app.state.http = httpx.AsyncClient(timeout=5.0)  # one outbound client for the whole app lifetime
        app.state.flaky_calls = 0
        try:
            yield
        finally:
            await app.state.http.aclose()
            engine.dispose()
            logger.info("stop")

    app = FastAPI(
        title="Student Manager API",
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        contact={"name": "Артур Лис", "email": "Artur.Lys@lnu.edu.ua"},
        license_info={"name": "MIT"},
    )
    app.include_router(students.router)
    app.include_router(groups.router)
    if include_debug or not settings.is_production:
        app.include_router(debug.router)
    register_health(app)
    register_exception_handlers(app)
    return app


def register_health(app: FastAPI) -> None:
    @app.get("/health", tags=["ops"], response_model=HealthOut, summary="Liveness/readiness: процес і база даних")
    async def health(request: Request) -> HealthOut:
        settings: Settings = request.app.state.settings
        database_ok = await asyncio.to_thread(request.app.state.store.ping)
        return HealthOut(
            status="ok" if database_ok else "degraded",
            version=__version__,
            app_env=settings.app_env,
            database="ok" if database_ok else "error",
        )


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
