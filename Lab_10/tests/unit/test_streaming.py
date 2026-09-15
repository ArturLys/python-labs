import logging
from collections import Counter
from inspect import isgenerator
from itertools import islice
from pathlib import Path

import pytest

from student_manager.analytics.processors import count_records_by_group
from student_manager.streaming.aggregates import (
    by_group,
    count_by_group,
    find_first,
    grade_changes,
    running_average,
    streaming_stats,
    top_n,
)
from student_manager.streaming.batching import Nested, adaptive_batches, batched, flatten
from student_manager.streaming.experiment import (
    eager_records,
    eager_stats,
    early_termination,
    lazy_stats,
    peak_memory,
    timed,
)
from student_manager.streaming.filters import head_by_id, in_groups, where, with_min_grade
from student_manager.streaming.generate import generate_rows, student_ids, write_dataset
from student_manager.streaming.models import StudentRecord
from student_manager.streaming.parsers import ValidationReport, parse_record, parse_rows, validate
from student_manager.streaming.pipeline import build_multi_pipeline, build_pipeline, export_csv, traced
from student_manager.streaming.readers import CsvDataset, LineReader, read_lines
from student_manager.streaming.transforms import tidy, to_grade_records

ROWS = 300


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "students.csv"
    write_dataset(path, ROWS, seed=1)
    return path


@pytest.fixture
def records() -> list[StudentRecord]:
    return [
        StudentRecord(1, "Гнатишин Марта", "ФЕП-31с", 95.0),
        StudentRecord(2, "Дзюба Остап", "ФЕП-31с", 81.0),
        StudentRecord(3, "Кравець Соломія", "ФЕП-32", 90.0),
        StudentRecord(4, "Скиба Юрій", "ФЕП-33", 73.0),
        StudentRecord(5, "Тимків Богдан", "ФЕП-33", 91.0),
    ]


def test_generate_rows_is_a_lazy_deterministic_generator() -> None:
    rows = generate_rows(5, seed=7)
    assert isgenerator(rows)
    assert list(rows) == list(generate_rows(5, seed=7))
    assert list(generate_rows(5, seed=7)) != list(generate_rows(5, seed=8))


def test_write_dataset_streams_rows_to_disk(csv_path: Path) -> None:
    lines = csv_path.read_text("utf-8").splitlines()
    assert len(lines) == ROWS + 1
    assert lines[0] == "student_id,name,group,grade"
    assert lines[97].endswith(",102.5") and lines[291].count(",") == 2  # deliberate defects


def test_line_reader_follows_iterator_protocol(csv_path: Path) -> None:
    reader = LineReader(csv_path)
    assert iter(reader) is reader
    assert next(reader).startswith("student_id")
    assert reader.lines_read == 1 and not reader.closed
    assert sum(1 for _ in reader) == ROWS
    assert reader.closed
    with pytest.raises(StopIteration):
        next(reader)
    assert list(reader) == []  # one-shot


def test_csv_dataset_is_a_reiterable_container(csv_path: Path) -> None:
    dataset = CsvDataset(csv_path)
    assert iter(dataset) is not dataset
    assert list(dataset) == list(dataset)


def test_read_lines_opens_late_and_closes_on_close(tmp_path: Path) -> None:
    lines = read_lines(tmp_path / "missing.csv")  # no error yet: nothing ran
    with pytest.raises(FileNotFoundError):
        next(lines)


def test_parse_record_reason_codes() -> None:
    assert parse_record(
        {"student_id": "7", "name": " Вовк Тарас ", "group": "ФЕП-31с", "grade": "88"}
    ) == StudentRecord(7, "Вовк Тарас", "ФЕП-31с", 88.0)
    bad = {
        "not_a_number": {"student_id": "7", "name": "x", "group": "g", "grade": "error"},
        "out_of_range": {"student_id": "7", "name": "x", "group": "g", "grade": "102"},
        "empty_field": {"student_id": "7", "name": " ", "group": "g", "grade": "50"},
        "missing_column": {"student_id": "7", "name": "x", "group": "g"},
    }
    for reason, row in bad.items():
        with pytest.raises(ValueError, match=reason):
            parse_record(row)


def test_validate_counts_rejections(csv_path: Path) -> None:
    report = ValidationReport()
    valid = list(validate(parse_rows(read_lines(csv_path)), report))
    assert report.seen == ROWS
    assert len(valid) == report.accepted == ROWS - 3
    assert report.rejected == Counter(out_of_range=1, empty_field=1, missing_column=1)


def test_tidy_fixes_dirty_rows() -> None:
    dirty = StudentRecord(13, "  гнатишин   марта", "феп-31с", 90.0)
    assert tidy(dirty) == StudentRecord(13, "Гнатишин Марта", "ФЕП-31с", 90.0)


def test_filters(records: list[StudentRecord]) -> None:
    assert [r.student_id for r in with_min_grade(records, 90)] == [1, 3, 5]
    assert [r.student_id for r in in_groups(records, ["ФЕП-33"])] == [4, 5]
    assert [r.student_id for r in where(records, lambda r: r.grade < 80)] == [4]
    assert [r.student_id for r in head_by_id(records, 2)] == [1, 2]


def test_batched_and_adaptive_batches() -> None:
    assert list(batched(range(10), 3)) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    assert [len(b) for b in adaptive_batches(range(40), start=1, limit=8)] == [1, 2, 4, 8, 8, 8, 8, 1]
    with pytest.raises(ValueError):
        next(batched([1], 0))


def test_flatten_is_recursive() -> None:
    nested: list[Nested[int]] = [1, [2, 3], [4, [5, [6]]]]
    assert list(flatten(nested)) == [1, 2, 3, 4, 5, 6]


def test_streaming_stats_matches_builtins(csv_path: Path) -> None:
    grades = [r.grade for r in build_pipeline(csv_path)]
    stats = streaming_stats(build_pipeline(csv_path))
    assert stats.count == len(grades) == ROWS - 3
    assert stats.average == pytest.approx(sum(grades) / len(grades))
    assert (stats.minimum, stats.maximum) == (min(grades), max(grades))
    assert sum(stats.per_group.values()) == stats.count


def test_top_n_and_count_by_group(records: list[StudentRecord]) -> None:
    assert [r.student_id for r in top_n(records, 2)] == [1, 5]
    assert count_by_group(records) == Counter({"ФЕП-31с": 2, "ФЕП-33": 2, "ФЕП-32": 1})


def test_running_average_and_grade_changes(records: list[StudentRecord]) -> None:
    assert list(running_average([80, 90, 100])) == [80, 85, 90]
    assert list(grade_changes(records[:3])) == [-14.0, 9.0]


def test_by_group_sorts_before_groupby(records: list[StudentRecord]) -> None:
    grouped = dict(by_group(reversed(records)))
    assert [len(members) for members in grouped.values()] == [2, 1, 2]
    assert list(grouped) == ["ФЕП-31с", "ФЕП-32", "ФЕП-33"]


def test_find_first_stops_reading_early(csv_path: Path) -> None:
    reader = LineReader(csv_path)
    hit = find_first(validate(parse_rows(reader)), lambda r: r.student_id == 20)
    assert hit is not None and hit.student_id == 20
    assert reader.lines_read == 21  # header + 20 rows, not 301
    reader.close()
    assert reader.closed


def test_pipeline_is_lazy_until_consumed(tmp_path: Path) -> None:
    pipeline = build_pipeline(tmp_path / "missing.csv")
    with pytest.raises(FileNotFoundError):
        next(pipeline)


def test_multi_file_chain_and_export(tmp_path: Path) -> None:
    parts = [tmp_path / "a.csv", tmp_path / "b.csv"]
    write_dataset(parts[0], 50, seed=1)
    write_dataset(parts[1], 60, seed=2)
    chained = list(build_multi_pipeline(parts, 0))
    assert len(chained) == len(list(build_pipeline(parts[0]))) + len(list(build_pipeline(parts[1])))
    out = tmp_path / "out.csv"
    assert export_csv(chained, out) == len(chained)
    assert list(build_pipeline(out)) == chained


def test_student_ids_is_infinite_but_sliceable() -> None:
    assert isgenerator(student_ids())
    assert list(islice(student_ids(5), 3)) == [5, 6, 7]


def test_eager_and_lazy_agree(csv_path: Path) -> None:
    assert eager_stats(csv_path, 85) == lazy_stats(csv_path, 85)
    assert eager_records(csv_path, 85) == list(build_pipeline(csv_path, 85))


def test_measurement_helpers(csv_path: Path) -> None:
    value, seconds = timed(lambda: sum(range(1000)))
    assert value == 499500 and seconds >= 0
    _, peak = peak_memory(lambda: [0] * 100_000)
    assert peak > 100_000 * 8
    result = early_termination(csv_path, ROWS, lambda r: r.student_id > 10, minimum=0)
    assert result.lazy_hit == result.eager_hit and result.lines_pulled < ROWS + 1


def test_traced_logs_only_when_drained(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="student_manager.streaming"):
        assert list(islice(traced("head", range(10)), 3)) == [0, 1, 2]
        assert caplog.records == []
        assert sum(traced("all", range(10))) == 45
    assert "stage all" in caplog.text and "10 items" in caplog.text


def test_to_grade_records_bridges_to_lab2(records: list[StudentRecord]) -> None:
    bridged = list(to_grade_records(records, "Мова С"))
    assert bridged[0].discipline == "Мова С" and bridged[0].student == "Гнатишин Марта"
    assert count_records_by_group(bridged)["ФЕП-33"] == 2
