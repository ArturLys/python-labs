"""Integration: YAML config -> import -> filter -> export -> summary, on real files in tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from student_manager.storage.config import load_config
from student_manager.storage.dataset import (
    INVALID_ROWS,
    valid_student_rows,
    write_demo_config,
    write_large_csv,
    write_students_csv,
)
from student_manager.storage.exceptions import DataError
from student_manager.storage.services import TOLERANT, ImportStatistics, import_students, run_pipeline


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    write_students_csv(tmp_path / "students.csv")
    (tmp_path / "output").mkdir()
    return tmp_path


def test_tolerant_run_exports_filters_and_writes_the_summary(workspace: Path) -> None:
    config = load_config(write_demo_config(workspace / "config.yaml"))
    result = run_pipeline(config)

    expected = sum(1 for row in valid_student_rows() if float(row[3]) >= 80)
    assert result.exported == expected
    assert result.statistics.invalid == len(INVALID_ROWS)
    exported = json.loads((workspace / "output" / "students.json").read_text(encoding="utf-8"))
    assert len(exported) == expected and all(item["grade"] >= 80 for item in exported)

    summary = json.loads((workspace / "output" / "summary.json").read_text(encoding="utf-8"))
    assert summary["exported"] == expected
    assert summary["statistics"]["invalid"] == len(INVALID_ROWS)
    errors = (workspace / "output" / "errors.csv").read_text(encoding="utf-8").splitlines()
    assert len(errors) == 1 + len(INVALID_ROWS)  # header + one line per rejected row


def test_strict_run_aborts_and_leaves_no_half_written_output(workspace: Path) -> None:
    config = load_config(write_demo_config(workspace / "config.yaml", skip_invalid=False))
    with pytest.raises(DataError):
        run_pipeline(config)
    assert not (workspace / "output" / "students.json").exists()


@pytest.mark.slow
def test_large_file_streams_through_tolerant_import(tmp_path: Path) -> None:
    path = write_large_csv(tmp_path / "large.csv", valid=2_000, invalid=20)
    statistics = ImportStatistics()
    count = sum(1 for _ in import_students(path, policy=TOLERANT, statistics=statistics))
    assert count == statistics.valid == 2_000
    assert statistics.invalid == 20
