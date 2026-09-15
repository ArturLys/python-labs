"""``python -m student_manager.api serve`` runs Uvicorn; ``... demo`` drives the API in-process through HTTPX."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from student_manager.api.app import create_app
from student_manager.api.client import StudentApiClient
from student_manager.settings import Settings, load_dotenv

SEED = [
    {
        "first_name": "Марта",
        "last_name": "Гнатишин",
        "group": "ФЕП-31с",
        "average_grade": 93.4,
        "email": "marta@lnu.edu.ua",
    },
    {"first_name": "Остап", "last_name": "Дзюба", "group": "ФЕП-31с", "average_grade": 78.9},
    {"first_name": "Соломія", "last_name": "Кравець", "group": "ФЕП-32", "average_grade": 88.1},
    {"first_name": "Тарас", "last_name": "Гаврилюк", "group": "ФЕП-32", "average_grade": 64.0},
]


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def dump(value: Any, limit: int = 600) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    return text if len(text) <= limit else text[:limit] + "\n  ..."


async def call(client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> Any:
    response = await client.request(method, path, **kwargs)
    body = f" json={json.dumps(kwargs['json'], ensure_ascii=False)}" if "json" in kwargs else ""
    print(f"> {method} {path}{body}")
    payload = response.json() if response.content else None
    print(f"< {response.status_code} {response.reason_phrase}" + (f"\n{dump(payload)}" if payload is not None else ""))
    return payload


async def demo(db_path: Path) -> None:
    logging.basicConfig(stream=sys.stdout, level=logging.WARNING, format="  [%(levelname)s] %(message)s")
    db_path.unlink(missing_ok=True)
    app = create_app(database_url=f"sqlite:///{db_path.as_posix()}", include_debug=True)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://api") as http:
        show("POST /students (201) і validation (422)")
        for payload in SEED:
            await call(http, "POST", "/students", json=payload)
        await call(
            http,
            "POST",
            "/students",
            json={"first_name": "Ігор", "last_name": "Новак", "group": "феп31", "average_grade": 150},
        )
        show("GET /students: query parameters (last_name, group, sort, page/size)")
        await call(http, "GET", "/students", params={"last_name": "гн"})
        await call(http, "GET", "/students", params={"group": "ФЕП-32", "sort": "-grade", "size": 1})
        show("GET /students/{id}, /students/best, 404")
        await call(http, "GET", "/students/1")
        await call(http, "GET", "/students/best", params={"group": "ФЕП-32"})
        await call(http, "GET", "/students/99")
        show("PATCH /students/{id}: бал, переведення; 409 на дублікат email")
        await call(http, "PATCH", "/students/2", json={"average_grade": 81.5})
        await call(http, "PATCH", "/students/4", json={"group": "ФЕП-41"})
        await call(http, "PATCH", "/students/3", json={"email": "marta@lnu.edu.ua"})
        show("DELETE /students/{id}: 204, потім 404")
        await call(http, "DELETE", "/students/3")
        await call(http, "DELETE", "/students/3")
        show("GET /groups/{code}/statistics і /groups/statistics?code=…&code=… (gather + Semaphore)")
        await call(http, "GET", "/groups/ФЕП-31с/statistics")
        await call(
            http,
            "GET",
            "/groups/statistics",
            params=[("code", "ФЕП-31с"), ("code", "ФЕП-32"), ("code", "ФЕП-41"), ("limit", 2)],
        )

    show("HTTPX-клієнт проти справжнього Uvicorn (127.0.0.1:8765): паралельні запити, timeout, retry з backoff")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(0.05)
    try:
        async with StudentApiClient(
            "http://127.0.0.1:8765", timeout=0.3, attempts=3, base_delay=0.05, concurrency=2
        ) as client:
            stats = await client.statistics_many(["ФЕП-31с", "ФЕП-32", "ФЕП-41"])
            print("  statistics_many ->", [(s["code"], s["students"], s["average"]) for s in stats])
            try:
                await client.get_json("/debug/slow", seconds=1.0)
            except httpx.TimeoutException as error:
                print(f"  /debug/slow?seconds=1.0 з timeout=0.3 -> {type(error).__name__} після 3 спроб")
            print("  /debug/flaky?failures=2 ->", await client.get_json("/debug/flaky", failures=2))
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m student_manager.api")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="запустити Uvicorn")
    serve.add_argument("--host", help="типово API_HOST")
    serve.add_argument("--port", type=int, help="типово API_PORT")
    serve.add_argument("--db", help="типово DATABASE_URL")
    sub.add_parser("demo", help="прогнати сценарій через httpx.ASGITransport без сервера")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        load_dotenv()  # development convenience; in Docker/CI the variables come from the environment itself
        settings = Settings.from_env()
        uvicorn.run(
            create_app(settings, database_url=args.db),
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            log_level=settings.log_level.lower(),
        )
    else:
        asyncio.run(demo(Path("data/api_demo.db")))


if __name__ == "__main__":
    main()
