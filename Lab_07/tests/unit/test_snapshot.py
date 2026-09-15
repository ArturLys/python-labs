"""Deterministic time through ``monkeypatch``: the snapshot's timestamp is whatever the test says it is."""

from __future__ import annotations

from datetime import datetime

import pytest

from student_manager import clock
from student_manager.registry import StudentRegistry
from student_manager.snapshot import registry_snapshot


def test_snapshot_uses_injected_clock(registry: StudentRegistry, frozen_clock: datetime) -> None:
    snapshot = registry_snapshot(registry)
    assert snapshot["generated_at"] == "2026-09-08T10:00:00+00:00"
    assert snapshot["total"] == 3
    assert snapshot["groups"]["ФЕП-31с"] == pytest.approx(86.2, abs=0.05)
    assert snapshot["excellent"] == ["Гнатишин Марта"]


def test_snapshot_is_reproducible(registry: StudentRegistry, frozen_clock: datetime) -> None:
    assert registry_snapshot(registry) == registry_snapshot(registry)


def test_clock_is_restored_after_the_patched_test() -> None:
    assert clock.now is clock._system_now
    assert clock.now().tzinfo is not None
