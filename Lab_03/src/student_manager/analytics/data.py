"""Input data set: one GradeRecord per (student, discipline) pair."""

from __future__ import annotations

from typing import NamedTuple


class GradeRecord(NamedTuple):
    """Immutable row (ПІБ, група, дисципліна, оцінка). A tuple, so it is hashable and can live in a set."""

    student: str
    group: str
    discipline: str
    grade: float


DISCIPLINES: tuple[str, ...] = ("Професійний Python", "Мова С", "Методи обчислень", "Інженерія даних")

# Compact source table: (студент, група, оцінки в порядку DISCIPLINES).
_RAW: list[tuple[str, str, tuple[float, ...]]] = [
    ("Гнатишин Марта", "ФЕП-31с", (95, 91, 94, 93)),
    ("Дзюба Остап", "ФЕП-31с", (81, 74, 79, 82)),
    ("Вовк Тарас", "ФЕП-31с", (88, 83, 85, 84)),
    ("Кравець Соломія", "ФЕП-32", (90, 86, 87, 89)),
    ("Пасічник Ірина", "ФЕП-32", (98, 96, 95, 97)),
    ("Мельник Андрій", "ФЕП-32", (77, 70, 72, 75)),
    ("Скиба Юрій", "ФЕП-33", (73, 68, 70, 74)),
    ("Ковальчук Назар", "ФЕП-33", (85, 80, 82, 83)),
    ("Тимків Богдан", "ФЕП-33", (91, 89, 90, 92)),
]


def load_records() -> list[GradeRecord]:
    """Unpack the compact table into flat records: one list comprehension over two loops."""
    return [
        GradeRecord(student, group, discipline, float(grade))
        for student, group, grades in _RAW
        for discipline, grade in zip(DISCIPLINES, grades, strict=True)
    ]
