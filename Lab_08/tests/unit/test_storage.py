import gzip
import inspect
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from student_manager.analytics.data import load_records
from student_manager.exceptions import InvalidGroupError, StudentManagerError
from student_manager.registry import StudentRegistry
from student_manager.storage import benchmark
from student_manager.storage.config import ProcessingConfig, load_config
from student_manager.storage.context import AtomicWriter, logged_operation
from student_manager.storage.dataset import write_demo_config, write_large_csv, write_students_csv
from student_manager.storage.dto import STUDENT_FIELDS, Row, StudentRow
from student_manager.storage.exceptions import (
    ConfigurationError,
    DataExportError,
    DataImportError,
    RecordValidationError,
    UnsupportedFormatError,
)
from student_manager.storage.exporters import to_json, write_rows
from student_manager.storage.logging_config import configure_logging, reset_logging
from student_manager.storage.readers import read_rows
from student_manager.storage.services import (
    STRICT,
    TOLERANT,
    ImportStatistics,
    error_report,
    export_grade_records,
    filter_by_grade,
    import_grade_records,
    import_students,
    run_pipeline,
)
from student_manager.storage.validators import parse_student_row, to_student

VALID_ROW: Row = {"student_id": "1", "name": "Гнатишин Марта", "group": "ФЕП-31с", "grade": "93.25",
                  "email": "marta@lnu.edu.ua"}


@pytest.fixture(autouse=True)
def _release_log_files() -> Iterator[None]:
    yield
    reset_logging()


@pytest.fixture
def students_csv(tmp_path: Path) -> Path:
    return write_students_csv(tmp_path / "students.csv")


@pytest.fixture
def config_path(tmp_path: Path, students_csv: Path) -> Path:
    (tmp_path / "output").mkdir()
    return write_demo_config(tmp_path / "config.yaml")


# --------------------------------------------------------------------------- validation

def test_parse_student_row_valid() -> None:
    assert parse_student_row(VALID_ROW, 2) == StudentRow(1, "Гнатишин Марта", "ФЕП-31с", 93.25, "marta@lnu.edu.ua")


@pytest.mark.parametrize(("field", "value", "cause"), [
    ("student_id", "abc", ValueError),
    ("student_id", "0", None),
    ("name", "", None),
    ("name", "Марта", None),
    ("grade", "wrong", ValueError),
    ("grade", "105", None),
    ("email", "marta-at-lnu", None),
    ("group", "31с", InvalidGroupError),
])
def test_invalid_field_is_reported_with_its_cause(field: str, value: str, cause: type[BaseException] | None) -> None:
    with pytest.raises(RecordValidationError) as info:
        parse_student_row({**VALID_ROW, field: value}, 7)
    assert (info.value.field, info.value.line_number) == (field, 7)
    if cause is None:
        assert info.value.__cause__ is None
    else:
        assert isinstance(info.value.__cause__, cause)


def test_storage_errors_extend_the_project_base_class() -> None:
    assert issubclass(RecordValidationError, StudentManagerError)
    assert issubclass(ConfigurationError, StudentManagerError)


def test_domain_conversion_splits_the_name() -> None:
    student = to_student(parse_student_row(VALID_ROW, 2))
    assert (student.last_name, student.first_name, student.average_grade) == ("Гнатишин", "Марта", 93.25)


def test_typed_values_from_json_are_accepted() -> None:
    row = parse_student_row({**VALID_ROW, "student_id": 1, "grade": 93.25}, 1)
    assert (row.student_id, row.grade) == (1, 93.25)


# --------------------------------------------------------------------------- readers

def test_csv_reader_is_a_generator_with_line_numbers(students_csv: Path) -> None:
    rows = read_rows(students_csv, required=STUDENT_FIELDS)
    assert inspect.isgenerator(rows)
    line_number, row = next(rows)
    assert line_number == 2 and row["name"] == "Гнатишин Марта"


def test_csv_missing_columns_fail_fast(tmp_path: Path) -> None:
    path = tmp_path / "wrong.csv"
    path.write_text("id,name\n1,x\n", encoding="utf-8")
    with pytest.raises(DataImportError, match="бракує колонок"):
        list(read_rows(path, required=STUDENT_FIELDS))


def test_missing_file_chains_the_oserror(tmp_path: Path) -> None:
    with pytest.raises(DataImportError) as info:
        list(read_rows(tmp_path / "missing.csv"))
    assert isinstance(info.value.__cause__, FileNotFoundError)


def test_broken_json_chains_the_decode_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('[{"a": 1}, oops', encoding="utf-8")
    with pytest.raises(DataImportError) as info:
        list(read_rows(path))
    assert isinstance(info.value.__cause__, json.JSONDecodeError)


def test_broken_yaml_chains_the_yaml_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("- a: [1, 2\n", encoding="utf-8")
    with pytest.raises(DataImportError) as info:
        list(read_rows(path))
    assert isinstance(info.value.__cause__, yaml.YAMLError)


def test_unknown_extension(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFormatError):
        list(read_rows(tmp_path / "grades.xml"))


def test_jsonl_skips_blank_lines_and_keeps_line_numbers(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert list(read_rows(path)) == [(1, {"a": 1}), (3, {"a": 2})]


# --------------------------------------------------------------------------- exporters and round trips

@pytest.mark.parametrize("name", ["grades.csv", "grades.json", "grades.jsonl", "grades.yaml", "grades.jsonl.gz", "grades.csv.gz"])
def test_grade_records_round_trip(tmp_path: Path, name: str) -> None:
    records = load_records()
    path = tmp_path / name
    assert export_grade_records(records, path) == 36
    statistics = ImportStatistics()
    assert list(import_grade_records(path, policy=STRICT, statistics=statistics)) == records
    assert statistics.valid == 36 and not (tmp_path / (name + ".tmp")).exists()


def test_gz_output_is_really_gzip(tmp_path: Path) -> None:
    path = tmp_path / "grades.jsonl.gz"
    export_grade_records(load_records()[:2], path)
    with gzip.open(path, "rt", encoding="utf-8") as file:
        assert file.readline().startswith('{"student": "Гнатишин Марта"')


def test_csv_exporter_writes_a_header_even_without_rows(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    assert write_rows([], path, fieldnames=("a", "b")) == 0
    assert path.read_bytes() == b"a,b\r\n"          # csv writes \r\n; newline="" keeps it verbatim


def test_custom_json_encoder() -> None:
    payload = {"p": Path("x"), "s": {2, 1}, "c": ProcessingConfig(60, True)}
    assert to_json(payload) == '{"p": "x", "s": [1, 2], "c": {"minimum_grade": 60, "skip_invalid": true, "progress_every": 0}}'


def test_unserialisable_value_is_an_export_error_and_leaves_nothing(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    with pytest.raises(DataExportError) as info:
        write_rows([{"x": object()}], path)
    assert isinstance(info.value.__cause__, TypeError)
    assert not path.exists() and not path.with_name("out.json.tmp").exists()


# --------------------------------------------------------------------------- context managers

def test_atomic_writer_replaces_on_success_and_keeps_a_backup(tmp_path: Path) -> None:
    path = tmp_path / "o.txt"
    path.write_text("old", encoding="utf-8")
    with AtomicWriter(path, backup=True) as file:
        file.write("new")
    assert path.read_text(encoding="utf-8") == "new"
    assert path.with_name("o.txt.bak").read_text(encoding="utf-8") == "old"
    assert not path.with_name("o.txt.tmp").exists()


def test_atomic_writer_keeps_the_old_output_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "o.txt"
    path.write_text("old", encoding="utf-8")
    with pytest.raises(RuntimeError), AtomicWriter(path) as file:
        file.write("half")
        raise RuntimeError("boom")
    assert path.read_text(encoding="utf-8") == "old"
    assert not path.with_name("o.txt.tmp").exists()


def test_atomic_writer_missing_directory_is_an_export_error(tmp_path: Path) -> None:
    with pytest.raises(DataExportError) as info, AtomicWriter(tmp_path / "nowhere" / "o.txt"):
        pass
    assert isinstance(info.value.__cause__, FileNotFoundError)


def test_logged_operation_logs_success_and_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    with logged_operation("op"):
        pass
    assert "op: початок" in caplog.text and "op: завершено" in caplog.text
    with pytest.raises(ValueError), logged_operation("bad"):
        raise ValueError("x")
    record = caplog.records[-1]
    assert record.levelno == logging.ERROR and record.exc_info is not None


def test_error_report_is_discarded_when_the_run_aborts(tmp_path: Path) -> None:
    path = tmp_path / "errors.csv"
    with pytest.raises(RuntimeError), error_report(path):
        raise RuntimeError("abort")
    assert not path.exists() and not path.with_name("errors.csv.tmp").exists()


# --------------------------------------------------------------------------- configuration

def test_load_config_resolves_paths_relative_to_the_file(config_path: Path, tmp_path: Path) -> None:
    config = load_config(config_path)
    assert config.input_path == tmp_path / "students.csv"
    assert config.output.path == tmp_path / "output" / "students.json"
    assert config.processing == ProcessingConfig(80.0, True, 5)
    assert (config.logging.level, config.logging.max_bytes) == ("INFO", 200_000)


def test_environment_overrides_the_file(config_path: Path) -> None:
    environ = {"STUDENT_MANAGER_MINIMUM_GRADE": "90", "STUDENT_MANAGER_SKIP_INVALID": "false"}
    config = load_config(config_path, environ=environ)
    assert (config.processing.minimum_grade, config.processing.skip_invalid) == (90.0, False)


@pytest.mark.parametrize(("old", "new", "message", "cause"), [
    ("minimum_grade: 80", "minimum_grade: 150", "minimum_grade", None),
    ("path: students.csv", "path: missing.csv", "вхідний файл", None),
    ("path: output/students.json", "path: nowhere/x.json", "каталог", None),
    ("level: INFO", "level: LOUD", "рівень", None),
    ("version: 1", "version: 2", "версія", None),
    ("input:\n  path: students.csv\n", "", "'input'", KeyError),
    ("skip_invalid: true", "skip_invalid: maybe", "логічним", ValueError),
    ("version: 1", "version: [oops", "YAML", yaml.YAMLError),
])
def test_configuration_errors(config_path: Path, old: str, new: str, message: str,
                              cause: type[BaseException] | None) -> None:
    config_path.write_text(config_path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message) as info:
        load_config(config_path)
    if cause is not None:
        assert isinstance(info.value.__cause__, cause)


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as info:
        load_config(tmp_path / "missing.yaml")
    assert isinstance(info.value.__cause__, FileNotFoundError)


# --------------------------------------------------------------------------- logging

def test_configure_logging_writes_to_the_file(tmp_path: Path) -> None:
    log = tmp_path / "logs" / "storage.log"
    configure_logging("DEBUG", log)
    logging.getLogger("student_manager.storage.test").warning("привіт, %s", "журнал")
    reset_logging()
    text = log.read_text(encoding="utf-8")
    assert "| WARNING  | student_manager.storage.test | привіт, журнал" in text


# --------------------------------------------------------------------------- pipeline

def test_tolerant_import_skips_and_counts(students_csv: Path) -> None:
    statistics = ImportStatistics()
    rows = list(import_students(students_csv, policy=TOLERANT, statistics=statistics))
    assert (statistics.total, statistics.valid, statistics.invalid) == (15, 9, 6)
    assert statistics.invalid_by_field == {"grade": 2, "name": 1, "student_id": 1, "email": 1, "group": 1}
    assert [row.student_id for row in rows] == list(range(1, 10))


def test_strict_import_stops_at_the_first_invalid_row(students_csv: Path) -> None:
    statistics = ImportStatistics()
    with pytest.raises(RecordValidationError) as info:
        list(import_students(students_csv, policy=STRICT, statistics=statistics))
    assert info.value.line_number == 11
    assert (statistics.total, statistics.valid, statistics.invalid) == (10, 9, 1)


def test_import_is_lazy(students_csv: Path) -> None:
    statistics = ImportStatistics()
    rows = import_students(students_csv, policy=TOLERANT, statistics=statistics)
    assert statistics.total == 0
    next(rows)
    assert statistics.total == 1


def test_filter_by_grade() -> None:
    rows = [StudentRow(1, "А Б", "ФЕП-31с", 79.9, "a@b.c"), StudentRow(2, "В Г", "ФЕП-31с", 80.0, "a@b.c")]
    assert [row.student_id for row in filter_by_grade(rows, 80)] == [2]


def test_pipeline_end_to_end(config_path: Path, tmp_path: Path) -> None:
    result = run_pipeline(load_config(config_path))
    assert (result.exported, result.statistics.valid, result.statistics.invalid) == (6, 9, 6)
    exported = json.loads((tmp_path / "output" / "students.json").read_text(encoding="utf-8"))
    assert [item["student_id"] for item in exported] == [1, 3, 4, 5, 8, 9]
    assert len((tmp_path / "output" / "errors.csv").read_text(encoding="utf-8").splitlines()) == 1 + 6
    summary = json.loads((tmp_path / "output" / "summary.json").read_text(encoding="utf-8"))
    assert summary["statistics"]["invalid"] == 6 and summary["exported"] == 6


def test_strict_pipeline_leaves_the_previous_output_intact(config_path: Path, tmp_path: Path) -> None:
    run_pipeline(load_config(config_path))
    output = tmp_path / "output" / "students.json"
    before = output.read_bytes()
    strict = load_config(write_demo_config(tmp_path / "strict.yaml", skip_invalid=False))
    with pytest.raises(RecordValidationError):
        run_pipeline(strict)
    assert output.read_bytes() == before
    assert not list((tmp_path / "output").glob("*.tmp"))


def test_export_feeds_the_registry(config_path: Path, tmp_path: Path) -> None:
    run_pipeline(load_config(config_path))
    output = tmp_path / "output" / "students.json"
    registry = StudentRegistry(to_student(parse_student_row(row, n)) for n, row in read_rows(output))
    assert len(registry) == 6 and registry.best().full_name == "Пасічник Ірина"


# --------------------------------------------------------------------------- experiments

def test_strict_vs_tolerant_experiment(tmp_path: Path) -> None:
    strict, tolerant = benchmark.strict_vs_tolerant(tmp_path, valid=50, invalid=5)
    assert (strict.total, strict.valid, strict.invalid, strict.exported, strict.output_exists) == (11, 10, 1, 0, False)
    assert (tolerant.total, tolerant.valid, tolerant.invalid, tolerant.exported, tolerant.output_exists) == (55, 50, 5, 50, True)


def test_eager_and_streaming_read_the_same_rows(tmp_path: Path) -> None:
    path = write_large_csv(tmp_path / "big.csv", valid=100)
    assert len(benchmark.eager_import(path)) == sum(1 for _ in benchmark.streaming_import(path)) == 100
