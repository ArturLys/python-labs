"""Synthetic but valid students for the experiments: deterministic (seeded), any size."""

from __future__ import annotations

import random

from student_manager.models import Student

GROUPS: tuple[str, ...] = tuple(f"ФЕП-{year}{number}" for year in (2, 3, 4) for number in range(1, 8))[:20]
FIRST_NAMES = ("Марта", "Остап", "Соломія", "Тарас", "Ярина", "Роман", "Оксана", "Богдан", "Христина", "Олег")
LAST_NAMES = ("Гнатишин", "Дзюба", "Кравець", "Гаврилюк", "Бойко", "Скиба", "Шевчук", "Мельник", "Савчук",
              "Петришин", "Козак", "Ткаченко")


def make_students(count: int, seed: int = 42) -> list[Student]:
    """`count` students spread over 20 groups with grades in 40.0..100.0 (one decimal)."""
    rng = random.Random(seed)
    return [
        Student(rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES), rng.choice(GROUPS), round(rng.uniform(40, 100), 1))
        for _ in range(count)
    ]
