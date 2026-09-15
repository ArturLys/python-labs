import pytest

from student_manager.analytics.analytics import (
    above_threshold,
    best_student,
    group_averages,
    make_record,
    make_threshold_filter,
    mean_of,
    pipeline,
    ranking,
    student_averages,
)
from student_manager.analytics.data import GradeRecord, load_records
from student_manager.analytics.processors import (
    count_records_by_group,
    filter_items,
    index_by_student,
    nested_grouping,
    students_per_group,
    unique_groups,
)


@pytest.fixture
def records() -> list[GradeRecord]:
    return load_records()


def test_every_student_has_a_grade_per_discipline(records: list[GradeRecord]) -> None:
    assert len(records) == 9 * 4
    assert all(len(rows) == 4 for rows in index_by_student(records).values())


def test_unique_groups(records: list[GradeRecord]) -> None:
    assert unique_groups(records) == {"ФЕП-31с", "ФЕП-32", "ФЕП-33"}


def test_student_average(records: list[GradeRecord]) -> None:
    assert student_averages(records)["Гнатишин Марта"] == pytest.approx(93.25)


def test_best_student(records: list[GradeRecord]) -> None:
    assert best_student(records) == ("Пасічник Ірина", 96.5)


def test_ranking_is_descending(records: list[GradeRecord]) -> None:
    averages = [avg for _, avg in ranking(records)]
    assert averages == sorted(averages, reverse=True)


def test_threshold_closure_remembers_minimum() -> None:
    at_least_90 = make_threshold_filter(90)
    assert at_least_90(("x", 90.0)) and not at_least_90(("y", 89.9))


def test_above_threshold(records: list[GradeRecord]) -> None:
    assert [s for s, _ in above_threshold(records, 90)] == ["Пасічник Ірина", "Гнатишин Марта", "Тимків Богдан"]


def test_counts_and_students_per_group(records: list[GradeRecord]) -> None:
    assert count_records_by_group(records)["ФЕП-32"] == 12
    assert students_per_group(records) == {"ФЕП-31с": 3, "ФЕП-32": 3, "ФЕП-33": 3}


def test_nested_grouping(records: list[GradeRecord]) -> None:
    assert len(nested_grouping(records)["ФЕП-33"]["Мова С"]) == 3


def test_group_averages(records: list[GradeRecord]) -> None:
    assert group_averages(records)["ФЕП-33"] == pytest.approx(977 / 12)


def test_args_and_kwargs() -> None:
    assert mean_of() == 0.0
    assert mean_of(1, 2, 3) == 2.0
    record = make_record(student="A", group="ФЕП-31с", discipline="Мова С", grade=70.0)
    assert record.grade == 70.0


def test_filter_and_pipeline(records: list[GradeRecord]) -> None:
    python_only = filter_items(records, lambda r: r.discipline == "Професійний Python")
    assert len(python_only) == 9
    top_two = pipeline(ranking(records), lambda s: s[:2])
    assert [name for name, _ in top_two] == ["Пасічник Ірина", "Гнатишин Марта"]
