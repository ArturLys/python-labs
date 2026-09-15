"""Integration: real files in tmp_path through import -> registry -> export -> import again."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from student_manager.registry import StudentRegistry
from student_manager.storage.dto import STUDENT_FIELDS
from student_manager.storage.exceptions import DataError
from student_manager.storage.exporters import write_rows
from student_manager.storage.services import STRICT, ImportPolicy, ImportStatistics, import_students

from tests.conftest import CsvWriter

VALID_ROWS = [
    [1, "Гнатишин Марта", "ФЕП-31с", 93.4, "marta@lnu.edu.ua"],
    [2, "Дзюба Остап", "ФЕП-31с", 78.9, "ostap@lnu.edu.ua"],
    [3, "Кравець Соломія", "ФЕП-32", 88.1, "solomiia@lnu.edu.ua"],
]


def test_csv_to_registry_to_json_and_back(write_csv: CsvWriter, tmp_path: Path) -> None:
    source = write_csv(VALID_ROWS)
    statistics = ImportStatistics()
    rows = list(import_students(source, policy=STRICT, statistics=statistics))
    assert statistics.valid == 3

    registry = StudentRegistry(row.to_student() for row in rows)
    assert registry.best().full_name == "Гнатишин Марта"
    assert registry.group_average("ФЕП-31с") == pytest.approx(86.15)

    target = tmp_path / "export.json"
    assert write_rows((row.to_dict() for row in rows), target, fieldnames=STUDENT_FIELDS) == 3
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert [item["name"] for item in payload] == ["Гнатишин Марта", "Дзюба Остап", "Кравець Соломія"]

    again = list(import_students(target, policy=STRICT, statistics=ImportStatistics()))
    assert again == rows


def test_malformed_rows_follow_the_policy(write_csv: CsvWriter, policy: ImportPolicy) -> None:
    source = write_csv(VALID_ROWS[:1] + [
        [2, "Дзюба Остап", "ФЕП-31с", "сто", "ostap@lnu.edu.ua"],  # grade is not a number
        [3, "Кравець Соломія", "ФЕП-32", 188.1, "solomiia@lnu.edu.ua"],  # grade out of range
    ])
    statistics = ImportStatistics()
    if policy.skip_invalid:
        rows = list(import_students(source, policy=policy, statistics=statistics))
        assert [row.student_id for row in rows] == [1]
        assert statistics.valid == 1
    else:
        with pytest.raises(DataError):
            list(import_students(source, policy=policy, statistics=statistics))
        assert statistics.valid == 1  # the first row was already accepted when the second failed


def test_missing_column_is_rejected_before_any_row(tmp_path: Path) -> None:
    source = tmp_path / "no_email.csv"
    source.write_text("student_id,name,group,grade\n1,Гнатишин Марта,ФЕП-31с,93.4\n", encoding="utf-8")
    with pytest.raises(DataError):
        list(import_students(source, policy=STRICT, statistics=ImportStatistics()))
