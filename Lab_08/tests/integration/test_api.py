"""API tests: the FastAPI app is driven in-process through httpx.ASGITransport; no server, a fresh DB per test."""

from __future__ import annotations

import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from student_manager.api import StudentApiClient, create_app, gather_statistics
from student_manager.api.schemas import GroupStatisticsOut

MARTA = {"first_name": "Марта", "last_name": "Гнатишин", "group": "ФЕП-31с", "average_grade": 93.4,
         "email": "marta@lnu.edu.ua"}
OSTAP = {"first_name": "Остап", "last_name": "Дзюба", "group": "ФЕП-31с", "average_grade": 78.9}
SOLOMIIA = {"first_name": "Соломія", "last_name": "Кравець", "group": "ФЕП-32", "average_grade": 88.1}


@pytest_asyncio.fixture
async def api(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(database_url=f"sqlite:///{(tmp_path / 'api.db').as_posix()}", include_debug=True)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def seeded(api: httpx.AsyncClient) -> httpx.AsyncClient:
    for payload in (MARTA, OSTAP, SOLOMIIA):
        assert (await api.post("/students", json=payload)).status_code == 201
    return api


# --- CRUD and status codes ---------------------------------------------------------------------------------------


async def test_list_is_empty_initially(api: httpx.AsyncClient) -> None:
    response = await api.get("/students")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


async def test_post_returns_201_and_the_created_resource(api: httpx.AsyncClient) -> None:
    response = await api.post("/students", json=MARTA)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "full_name": "Гнатишин Марта", **MARTA}


@pytest.mark.parametrize(("field", "value"), [
    ("average_grade", 150), ("average_grade", -1), ("group", "феп31"), ("first_name", "  "), ("email", "not-an-email"),
])
async def test_validation_errors_are_422(api: httpx.AsyncClient, field: str, value: object) -> None:
    response = await api.post("/students", json={**MARTA, field: value})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


async def test_unknown_field_is_rejected(api: httpx.AsyncClient) -> None:
    assert (await api.post("/students", json={**MARTA, "age": 20})).status_code == 422


async def test_get_missing_student_is_404_with_structured_error(api: httpx.AsyncClient) -> None:
    response = await api.get("/students/99")
    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "у таблиці students немає запису з id=99"}


async def test_patch_grade_then_transfer(seeded: httpx.AsyncClient) -> None:
    assert (await seeded.patch("/students/2", json={"average_grade": 81.5})).json()["average_grade"] == 81.5
    moved = (await seeded.patch("/students/2", json={"group": "ФЕП-41"})).json()
    assert moved["group"] == "ФЕП-41" and moved["average_grade"] == 81.5
    assert (await seeded.patch("/students/2", json={})).status_code == 422
    assert (await seeded.patch("/students/99", json={"average_grade": 1})).status_code == 404


async def test_delete_is_204_then_404(seeded: httpx.AsyncClient) -> None:
    assert (await seeded.delete("/students/1")).status_code == 204
    assert (await seeded.delete("/students/1")).status_code == 404
    assert (await seeded.get("/students")).json()["total"] == 2


async def test_duplicate_email_is_409(seeded: httpx.AsyncClient) -> None:
    response = await seeded.post("/students", json={**OSTAP, "email": "marta@lnu.edu.ua"})
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


# --- query parameters ----------------------------------------------------------------------------------------------


async def test_search_filter_sort_and_pagination(seeded: httpx.AsyncClient) -> None:
    by_name = (await seeded.get("/students", params={"last_name": "гн"})).json()
    assert [s["full_name"] for s in by_name["items"]] == ["Гнатишин Марта"]
    by_group = (await seeded.get("/students", params={"group": "ФЕП-31с", "sort": "-grade"})).json()
    assert [s["last_name"] for s in by_group["items"]] == ["Гнатишин", "Дзюба"]
    page = (await seeded.get("/students", params={"sort": "grade", "page": 2, "size": 2})).json()
    assert page["total"] == 3 and [s["last_name"] for s in page["items"]] == ["Гнатишин"]
    assert (await seeded.get("/students", params={"size": 0})).status_code == 422


async def test_best_student_overall_and_in_group(seeded: httpx.AsyncClient) -> None:
    assert (await seeded.get("/students/best")).json()["last_name"] == "Гнатишин"
    assert (await seeded.get("/students/best", params={"group": "ФЕП-32"})).json()["last_name"] == "Кравець"


async def test_group_endpoints(seeded: httpx.AsyncClient) -> None:
    students = (await seeded.get("/groups/ФЕП-31с/students")).json()
    assert [s["last_name"] for s in students] == ["Гнатишин", "Дзюба"]
    stats = (await seeded.get("/groups/ФЕП-31с/statistics")).json()
    assert stats["students"] == 2 and stats["average"] == pytest.approx(86.15) and stats["best"]["id"] == 1
    assert (await seeded.get("/groups/ФЕП-99/statistics")).status_code == 404
    many = (await seeded.get("/groups/statistics", params=[("code", "ФЕП-32"), ("code", "ФЕП-31с")])).json()
    assert [g["code"] for g in many] == ["ФЕП-32", "ФЕП-31с"]  # gather keeps the request order


# --- asyncio: Task, gather, Semaphore, timeout ------------------------------------------------------------------------


class SlowSource:
    """Fake statistics source that records how many calls overlap in time."""

    def __init__(self, delay: float) -> None:
        self.delay, self.active, self.peak, self._lock = delay, 0, 0, threading.Lock()

    def group_statistics(self, code: str) -> GroupStatisticsOut:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay)
        with self._lock:
            self.active -= 1
        return GroupStatisticsOut(code=code, students=0, average=None, best=None)


async def test_semaphore_caps_concurrency() -> None:
    codes = [f"Г-{i}" for i in range(6)]
    limited = SlowSource(0.03)
    result = await gather_statistics(limited, codes, limit=2)
    assert [g.code for g in result] == codes and limited.peak <= 2
    unlimited = SlowSource(0.03)
    await gather_statistics(unlimited, codes, limit=6)
    assert unlimited.peak >= 3


async def test_timeout_inside_gather() -> None:
    with pytest.raises(TimeoutError):
        await gather_statistics(SlowSource(0.3), ["Г-1"], timeout=0.05)


# --- HTTPX client: retry, backoff, timeout, parallel requests -------------------------------------------------------


async def test_client_retries_503_then_succeeds() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"ok": True})

    async with StudentApiClient("http://mock", transport=httpx.MockTransport(handler), attempts=3, base_delay=0) as client:
        assert await client.get_json("/ping") == {"ok": True}
    assert calls == ["/ping"] * 3


async def test_client_gives_up_after_attempts_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("повільний сервер", request=request)

    async with StudentApiClient("http://mock", transport=httpx.MockTransport(handler), attempts=2, base_delay=0) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.get_json("/anything")


async def test_client_parallel_statistics_against_the_app(tmp_path: Path) -> None:
    app = create_app(database_url=f"sqlite:///{(tmp_path / 'client.db').as_posix()}")
    async with app.router.lifespan_context(app):
        async with StudentApiClient("http://api", transport=httpx.ASGITransport(app=app), concurrency=2) as client:
            for payload in (MARTA, OSTAP, SOLOMIIA):
                await client.create_student(payload)
            stats = await client.statistics_many(["ФЕП-31с", "ФЕП-32"])
            assert [(s["code"], s["students"]) for s in stats] == [("ФЕП-31с", 2), ("ФЕП-32", 1)]
            with pytest.raises(httpx.HTTPStatusError):
                await client.statistics("ФЕП-99")
