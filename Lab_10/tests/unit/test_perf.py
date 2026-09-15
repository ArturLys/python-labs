"""Correctness of every optimised implementation against the loop baseline, plus cache and race behaviour."""

from __future__ import annotations

from functools import partial

import pytest

from student_manager.models import Student
from student_manager.perf import (
    GroupStatisticsService,
    compute_stats,
    compute_stats_numpy_from_students,
    make_students,
    measure,
    peak_memory,
    profile_top,
    race,
    stats_close,
    stats_processes,
    stats_raw_threads,
    stats_threads,
)
from student_manager.perf.parallel import (
    merge,
    partial_stats,
    partial_stats_columns,
    split,
    stats_processes_columns,
    to_columns,
)


@pytest.fixture(scope="module")
def students() -> list[Student]:
    return make_students(5_000, seed=7)


def test_baseline_values(students: list[Student]) -> None:
    stats = compute_stats(students)
    grades = [s.average_grade for s in students]
    assert stats.count == 5_000
    assert stats.mean == pytest.approx(sum(grades) / len(grades))
    assert (stats.minimum, stats.maximum) == (min(grades), max(grades))
    assert stats.ranking[0] == grades.index(max(grades))  # ties: first occurrence wins, like sorted(reverse=True)
    assert sum(stats.group_means.values()) / len(stats.group_means) == pytest.approx(stats.mean, abs=1.0)


def test_baseline_rejects_empty() -> None:
    with pytest.raises(ValueError):
        compute_stats([])


@pytest.mark.parametrize(
    "implementation",
    [
        partial(stats_threads, workers=3),
        partial(stats_raw_threads, workers=3),
        compute_stats_numpy_from_students,
    ],
    ids=["threads", "raw-threads", "numpy"],
)
def test_optimised_versions_match_baseline(students: list[Student], implementation: object) -> None:
    assert stats_close(compute_stats(students), implementation(students))  # type: ignore[operator]


@pytest.mark.slow
def test_process_pool_matches_baseline(students: list[Student]) -> None:
    assert stats_close(compute_stats(students), stats_processes(students, workers=2))
    assert stats_close(compute_stats(students), stats_processes_columns(to_columns(students), workers=2))


def test_columns_variant_matches_baseline_in_process(students: list[Student]) -> None:
    columns = to_columns(students)
    pieces = split(students, 3)
    parts = [
        partial_stats_columns(columns.grades[o : o + len(c)], columns.group_ids[o : o + len(c)], o) for o, c in pieces
    ]
    assert stats_close(compute_stats(students), merge(parts, columns.codes))


def test_lost_updates_appear_with_a_tiny_switch_interval() -> None:
    assert race(50_000, threads=4, use_lock=True, switch_interval=1e-6) == 200_000
    assert race(50_000, threads=4, use_lock=False, switch_interval=1e-6) < 200_000


def test_split_covers_everything_and_merge_is_exact(students: list[Student]) -> None:
    pieces = split(students, 7)
    assert sum(len(chunk) for _, chunk in pieces) == len(students)
    assert [offset for offset, _ in pieces] == sorted(offset for offset, _ in pieces)
    merged = merge(partial_stats(chunk, offset) for offset, chunk in pieces)
    assert stats_close(compute_stats(students), merged)


def test_cache_hits_misses_and_invalidation(students: list[Student]) -> None:
    service = GroupStatisticsService(students)
    first = service.group_statistics("ФЕП-31")
    assert service.group_statistics("ФЕП-31") == first
    assert service.info() == (1, 1, 1)
    service.add(Student("Новий", "Студент", "ФЕП-31", 100.0))
    assert service.group_statistics("ФЕП-31").maximum == 100.0  # new version -> recomputed
    assert service.info()[1] == 2
    service.invalidate()
    assert service.info() == (0, 0, 0)
    with pytest.raises(KeyError):
        service.group_statistics("НЕМА-00")


def test_lock_prevents_lost_updates() -> None:
    assert race(20_000, threads=4, use_lock=True) == 80_000
    assert race(20_000, threads=4, use_lock=False) <= 80_000


def test_measuring_tools(students: list[Student]) -> None:
    timing = measure("baseline", partial(compute_stats, students), repeats=2)
    assert timing.best > 0 and timing.best <= timing.mean and len(timing.runs) == 2
    assert timing.speedup(timing) == 1.0
    result, peak = peak_memory(partial(compute_stats, students))
    assert result.count == 5_000 and peak > 0
    assert "compute_stats" in profile_top(partial(compute_stats, students))
