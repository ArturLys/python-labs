"""Configuration through the real process environment, isolated with ``monkeypatch.setenv``/``delenv``."""

from __future__ import annotations

from pathlib import Path

import pytest

from student_manager.storage.config import load_config
from student_manager.storage.dataset import write_demo_config, write_students_csv
from student_manager.storage.exceptions import ConfigurationError


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    write_students_csv(tmp_path / "students.csv")
    (tmp_path / "output").mkdir()
    return write_demo_config(tmp_path / "config.yaml")


def test_environment_variable_beats_the_file(config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUDENT_MANAGER_MINIMUM_GRADE", "90")
    monkeypatch.setenv("STUDENT_MANAGER_SKIP_INVALID", "false")
    config = load_config(config_path)
    assert config.processing.minimum_grade == 90
    assert config.processing.skip_invalid is False


def test_environment_is_clean_again_in_the_next_test(config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STUDENT_MANAGER_MINIMUM_GRADE", raising=False)
    config = load_config(config_path)
    assert config.processing.minimum_grade == 80  # the value from the YAML file
    assert config.processing.skip_invalid is True


@pytest.mark.parametrize("value", ["150", "-1", "abc"])
def test_invalid_override_is_a_configuration_error(config_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                   value: str) -> None:
    monkeypatch.setenv("STUDENT_MANAGER_MINIMUM_GRADE", value)
    with pytest.raises(ConfigurationError):
        load_config(config_path)


def test_paths_are_resolved_relative_to_the_config_file(config_path: Path, tmp_path: Path) -> None:
    config = load_config(config_path)
    assert config.input_path == tmp_path / "students.csv"
    assert config.output.path == tmp_path / "output" / "students.json"
    assert config.output.summary_path is not None and config.output.summary_path.parent == tmp_path / "output"
