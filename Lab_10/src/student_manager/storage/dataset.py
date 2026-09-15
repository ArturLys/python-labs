"""Generators of input files: the demo data set (the nine students of lab 2 plus deliberately broken rows)
and large synthetic CSVs for the experiments. The files live under data/ (git-ignored); this is committed."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

from student_manager.analytics.data import load_records
from student_manager.analytics.processors import index_by_student
from student_manager.storage.context import open_text
from student_manager.storage.dto import STUDENT_FIELDS

EMAILS: dict[str, str] = {
    "Гнатишин Марта": "marta.hnatyshyn@lnu.edu.ua",
    "Дзюба Остап": "ostap.dziuba@lnu.edu.ua",
    "Вовк Тарас": "taras.vovk@lnu.edu.ua",
    "Кравець Соломія": "solomiia.kravets@lnu.edu.ua",
    "Пасічник Ірина": "iryna.pasichnyk@lnu.edu.ua",
    "Мельник Андрій": "andrii.melnyk@lnu.edu.ua",
    "Скиба Юрій": "yurii.skyba@lnu.edu.ua",
    "Ковальчук Назар": "nazar.kovalchuk@lnu.edu.ua",
    "Тимків Богдан": "bohdan.tymkiv@lnu.edu.ua",
}

# One broken field per row, one row per validation rule. (line numbers 11..16 in the demo file)
INVALID_ROWS: list[list[str]] = [
    ["10", "", "ФЕП-31с", "76.0", "noname@lnu.edu.ua"],  # name empty
    ["11", "Новак Петро", "ФЕП-33", "105", "petro.novak@lnu.edu.ua"],  # grade out of range
    ["abc", "Бойко Марія", "ФЕП-32", "85", "mariia.boiko@lnu.edu.ua"],  # id not a number
    ["13", "Литвин Андрій", "ФЕП-31с", "wrong", "andrii.lytvyn@lnu.edu.ua"],  # grade not a number
    ["14", "Шевчук Олена", "ФЕП-32", "88.5", "olena.shevchuk-at-lnu"],  # email
    ["15", "Романюк Ігор", "31с", "79", "ihor.romaniuk@lnu.edu.ua"],  # group pattern (lab-1 model)
]

DEMO_CONFIG = """\
# Конфігурація демонстрації ЛР5. Шляхи — відносно цього файла.
version: 1

input:
  path: students.csv

output:
  path: output/students.json
  errors_path: output/errors.csv
  summary_path: output/summary.json
  backup: true

processing:
  minimum_grade: 80
  skip_invalid: true          # tolerant mode; false = strict
  progress_every: 5

logging:
  level: INFO
  path: logs/storage.log
  max_bytes: 200000
  backup_count: 2
"""


def valid_student_rows() -> list[list[str]]:
    """Nine real students: id in lab-2 order, grade = mean of the four disciplines."""
    by_student = index_by_student(load_records())
    return [
        [str(number), student, records[0].group, f"{mean(r.grade for r in records):g}", EMAILS[student]]
        for number, (student, records) in enumerate(by_student.items(), start=1)
    ]


def write_students_csv(path: Path, *, include_invalid: bool = True) -> Path:
    rows = valid_student_rows() + (INVALID_ROWS if include_invalid else [])
    with open_text(path, "w") as file:
        writer = csv.writer(file)
        writer.writerow(STUDENT_FIELDS)
        writer.writerows(rows)
    return path


def write_demo_config(path: Path, **overrides: object) -> Path:
    """The YAML above, with `key: value` lines replaced for the experiments (skip_invalid=False, ...)."""
    lines = []
    for line in DEMO_CONFIG.splitlines():
        key = line.split(":", 1)[0].strip()
        if key in overrides:
            line = f"{line.split(key, 1)[0]}{key}: {str(overrides[key]).lower()}"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_large_csv(path: Path, *, valid: int, invalid: int = 0) -> Path:
    """`valid` synthetic students plus `invalid` rows with a non-numeric grade, spread evenly through the file."""
    step = (valid // invalid) if invalid else 0
    with open_text(path, "w") as file:
        writer = csv.writer(file)
        writer.writerow(STUDENT_FIELDS)
        broken = 0
        for i in range(1, valid + 1):
            writer.writerow([i, f"Студент-{i:06d} Тест", f"ФЕП-{31 + i % 3}", f"{60 + i % 41}", f"s{i:06d}@lnu.edu.ua"])
            if step and i % step == 0 and broken < invalid:
                broken += 1
                writer.writerow(
                    [valid + broken, f"Зламаний-{broken:03d} Запис", "ФЕП-31с", "wrong", f"bad{broken}@lnu.edu.ua"]
                )
    return path
