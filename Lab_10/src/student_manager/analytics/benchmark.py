"""Experiment: linear search in a list vs lookup in a dict index, 1 000 / 10 000 / 100 000 records."""

from __future__ import annotations

import random
from timeit import timeit

from student_manager.analytics.data import DISCIPLINES, GradeRecord

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)
LOOKUPS = 50


def make_records(count: int, seed: int = 42) -> list[GradeRecord]:
    rng = random.Random(seed)
    return [
        GradeRecord(
            f"Студент-{i:06d}",
            f"ФЕП-{rng.randint(11, 43)}",
            DISCIPLINES[i % len(DISCIPLINES)],
            float(rng.randint(60, 100)),
        )
        for i in range(count)
    ]


def find_linear(records: list[GradeRecord], student: str) -> GradeRecord | None:
    for record in records:  # O(n): every miss walks the whole list
        if record.student == student:
            return record
    return None


def run(sizes: tuple[int, ...] = SIZES, lookups: int = LOOKUPS) -> list[tuple[int, float, float, float]]:
    """Return (n, list µs/lookup, dict µs/lookup, speedup) for every size."""
    rows = []
    for n in sizes:
        records = make_records(n)
        index = {r.student: r for r in records}  # dict comprehension, O(n) once
        rng = random.Random(7)
        targets = [records[rng.randrange(n)].student for _ in range(lookups)]
        list_s = timeit(lambda: [find_linear(records, t) for t in targets], number=1) / lookups
        dict_s = timeit(lambda: [index.get(t) for t in targets], number=1) / lookups
        rows.append((n, list_s * 1e6, dict_s * 1e6, list_s / dict_s))
    return rows


def format_table(rows: list[tuple[int, float, float, float]]) -> str:
    lines = [f"{'records':>9} {'list, µs':>12} {'dict, µs':>12} {'speedup':>10}", "-" * 46]
    lines += [f"{n:>9,} {list_us:>12.2f} {dict_us:>12.3f} {speedup:>9.0f}x" for n, list_us, dict_us, speedup in rows]
    return "\n".join(lines).replace(",", " ")


if __name__ == "__main__":
    print(format_table(run()))
