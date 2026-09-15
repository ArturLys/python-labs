"""Test doubles: Mock/autospec for the synchronous mailer, AsyncMock for the asynchronous gateway.

Every test checks two things: the value the service returned and how it talked to its collaborator.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, call

import pytest

from student_manager.exceptions import StudentNotFoundError
from student_manager.notify import AsyncStudentService, DigestSender, Mailer, StudentGateway
from student_manager.notify.digest import DigestError
from student_manager.registry import StudentRegistry

from tests.conftest import StudentFactory

# --- DigestSender + Mock ---------------------------------------------------------------------------------------


def test_digest_sends_one_message_per_group(registry: StudentRegistry, mailer: Mailer) -> None:
    mailer.send.return_value = "msg-1"  # type: ignore[attr-defined]
    sent = DigestSender(mailer).send_all(registry)
    assert sent == {"ФЕП-31с": "msg-1", "ФЕП-32": "msg-1"}
    assert mailer.send.call_count == 2  # type: ignore[attr-defined]
    mailer.send.assert_any_call(  # type: ignore[attr-defined]
        "феп-31с@lnu.edu.ua", "Дайджест групи ФЕП-31с",
        "Середній бал: 86.2. Найкращий результат: Гнатишин Марта (93.4).",
    )


def test_message_ids_come_from_side_effect_sequence(registry: StudentRegistry, mailer: Mailer) -> None:
    mailer.send.side_effect = ["a", "b"]  # type: ignore[attr-defined]
    assert DigestSender(mailer).send_all(registry) == {"ФЕП-31с": "a", "ФЕП-32": "b"}


def test_transport_failure_is_wrapped_into_domain_error(registry: StudentRegistry, mailer: Mailer) -> None:
    mailer.send.side_effect = ["ok", ConnectionError("smtp down")]  # type: ignore[attr-defined]
    with pytest.raises(DigestError, match="ФЕП-32") as info:
        DigestSender(mailer).send_all(registry)
    assert isinstance(info.value.__cause__, ConnectionError)


def test_single_group_call_is_exact(mailer: Mailer, make_student: StudentFactory) -> None:
    registry = StudentRegistry([make_student(last_name="Новак", group="ФЕП-41", average_grade=70.0)])
    DigestSender(mailer, sender_domain="example.org").send_all(registry)
    mailer.send.assert_called_once_with(  # type: ignore[attr-defined]
        "феп-41@example.org", "Дайджест групи ФЕП-41",
        "Середній бал: 70.0. Найкращий результат: Новак Тест (70).",
    )


def test_autospec_rejects_a_wrong_signature(mailer: Mailer) -> None:
    with pytest.raises(TypeError):
        mailer.send("only-recipient")  # type: ignore[call-arg]


def test_empty_registry_sends_nothing(mailer: Mailer) -> None:
    assert DigestSender(mailer).send_all(StudentRegistry()) == {}
    mailer.send.assert_not_called()  # type: ignore[attr-defined]


# --- AsyncStudentService + AsyncMock ----------------------------------------------------------------------------


@pytest.fixture
def gateway() -> AsyncMock:
    """spec=Protocol: the async methods of the protocol become AsyncMocks, anything else is an AttributeError."""
    return AsyncMock(spec=StudentGateway)


def test_average_awaits_every_student(gateway: AsyncMock, make_student: StudentFactory) -> None:
    gateway.fetch.side_effect = [make_student(average_grade=80.0), make_student(average_grade=90.0)]
    service = AsyncStudentService(gateway)
    assert asyncio.run(service.average_of([1, 2])) == pytest.approx(85.0)
    assert gateway.fetch.await_count == 2
    gateway.fetch.assert_has_awaits([call(1), call(2)], any_order=True)


def test_missing_student_raises_and_is_awaited_once(gateway: AsyncMock) -> None:
    gateway.fetch.return_value = None
    with pytest.raises(StudentNotFoundError, match="id=42"):
        asyncio.run(AsyncStudentService(gateway).require(42))
    gateway.fetch.assert_awaited_once_with(42)


def test_empty_id_list_never_touches_the_gateway(gateway: AsyncMock) -> None:
    with pytest.raises(ValueError):
        asyncio.run(AsyncStudentService(gateway).average_of([]))
    gateway.fetch.assert_not_awaited()


def test_bump_grade_caps_at_hundred_and_saves(gateway: AsyncMock, make_student: StudentFactory) -> None:
    gateway.fetch.return_value = make_student(average_grade=97.5)
    updated = asyncio.run(AsyncStudentService(gateway).bump_grade(7, 5.0))
    assert updated.average_grade == 100.0
    gateway.save.assert_awaited_once_with(7, updated)


def test_gateway_error_propagates_unchanged(gateway: AsyncMock) -> None:
    gateway.fetch.side_effect = TimeoutError("gateway timeout")
    with pytest.raises(TimeoutError):
        asyncio.run(AsyncStudentService(gateway).average_of([1]))
