"""Data source: a generator of synthetic CSV rows and a streaming writer for hundreds of thousands of them."""

from __future__ import annotations

import csv
import random
from collections.abc import Iterator
from itertools import count, islice
from pathlib import Path

from student_manager.analytics.data import load_records
from student_manager.streaming.models import COLUMNS

_DEMO_NAMES = sorted({record.student for record in load_records()})  # the nine students of lab 2
LAST_NAMES: tuple[str, ...] = tuple(
    sorted(
        {name.split()[0] for name in _DEMO_NAMES}
        | {"Шевчук", "Бойко", "Лисенко", "Петришин", "Савчук", "Гаврилюк", "Іваськів"}
    )
)
FIRST_NAMES: tuple[str, ...] = tuple(
    sorted(
        {name.split()[1] for name in _DEMO_NAMES} | {"Оксана", "Роман", "Дарина", "Максим", "Христина", "Олег", "Ярина"}
    )
)
GROUPS: tuple[str, ...] = tuple(sorted({record.group for record in load_records()})) + ("ФЕП-34", "ФЕП-41")

DEFECT_EVERY = 97  # every 97th row is deliberately broken (four kinds of defect, in turn)
DIRTY_EVERY = 13  # every 13th row is valid but untidy: extra spaces, lower case


def student_ids(start: int = 1) -> Iterator[int]:
    """Infinite stream of identifiers on top of itertools.count(); always cut it with islice."""
    yield from count(start)


def _break(row: list[str], kind: int) -> list[str]:
    """Return a defective copy of the row: bad grade text, grade out of range, empty name, missing column."""
    student_id, name, group, grade = row
    match kind % 4:
        case 0:
            return [student_id, name, group, "error"]
        case 1:
            return [student_id, name, group, "102.5"]
        case 2:
            return [student_id, "", group, grade]
        case _:
            return [student_id, name, group]


def generate_rows(rows: int, seed: int = 3) -> Iterator[list[str]]:
    """Lazily yield `rows` CSV rows; the same seed always gives the same file."""
    rng = random.Random(seed)
    for student_id in islice(student_ids(), rows):
        name = f"{rng.choice(LAST_NAMES)} {rng.choice(FIRST_NAMES)}"
        group = rng.choice(GROUPS)
        grade = f"{rng.triangular(40, 100, 82):.1f}"
        row = [str(student_id), name, group, grade]
        if student_id % DEFECT_EVERY == 0:
            yield _break(row, student_id // DEFECT_EVERY)
        elif student_id % DIRTY_EVERY == 0:
            yield [row[0], "  " + name.lower().replace(" ", "   "), group.lower(), grade]
        else:
            yield row


def write_dataset(path: Path, rows: int, seed: int = 3) -> int:
    """Stream generated rows into a CSV file: one row is alive at a time. Returns the number written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for row in generate_rows(rows, seed):
            writer.writerow(row)
            written += 1
    return written


def ensure_dataset(path: Path, rows: int, seed: int = 3) -> Path:
    """Generate the file only when it is missing (the data directory is git-ignored)."""
    if not path.exists():
        write_dataset(path, rows, seed)
    return path
