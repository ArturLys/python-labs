"""External configuration: config.yaml -> frozen dataclasses, validated before any work starts (fail-fast).

    version: 1
    input:      {path}
    output:     {path, errors_path?, summary_path?, backup?}
    processing: {minimum_grade, skip_invalid, progress_every?}
    logging:    {level, path, max_bytes?, backup_count?}

Relative paths are relative to the directory of the config file, so the same file works from any cwd.
Environment variables STUDENT_MANAGER_* override single keys without touching the file.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from student_manager.config import GRADE_MAX, GRADE_MIN
from student_manager.storage.exceptions import ConfigurationError

SCHEMA_VERSION = 1
LOG_LEVELS: frozenset[str] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
ENV_PREFIX = "STUDENT_MANAGER_"
# environment variable suffix -> (section, key) it overrides
ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "INPUT_PATH": ("input", "path"),
    "OUTPUT_PATH": ("output", "path"),
    "MINIMUM_GRADE": ("processing", "minimum_grade"),
    "SKIP_INVALID": ("processing", "skip_invalid"),
    "LOG_LEVEL": ("logging", "level"),
}


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    minimum_grade: float
    skip_invalid: bool
    progress_every: int = 0


@dataclass(frozen=True, slots=True)
class OutputConfig:
    path: Path
    errors_path: Path | None = None
    summary_path: Path | None = None
    backup: bool = False


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str
    path: Path
    max_bytes: int = 1_000_000
    backup_count: int = 3


@dataclass(frozen=True, slots=True)
class AppConfig:
    version: int
    input_path: Path
    output: OutputConfig
    processing: ProcessingConfig
    logging: LoggingConfig


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    """The raw document. Three different low-level failures, three messages, every cause kept."""
    try:
        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"файл конфігурації не знайдено: {path}") from error
    except OSError as error:
        raise ConfigurationError(f"не вдалося прочитати конфігурацію {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"некоректний YAML у {path.name}: {str(error).splitlines()[0]}") from error
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{path.name}: конфігурація має бути YAML-mapping, а не {type(raw).__name__}")
    return raw


def apply_env_overrides(raw: dict[str, Any], environ: Mapping[str, str]) -> list[str]:
    """STUDENT_MANAGER_MINIMUM_GRADE=70 beats the file. Returns the variable names that were applied."""
    applied: list[str] = []
    for suffix, (section, key) in ENV_OVERRIDES.items():
        value = environ.get(ENV_PREFIX + suffix)
        if value is not None:
            raw.setdefault(section, {})[key] = value
            applied.append(ENV_PREFIX + suffix)
    return applied


def _section(raw: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    section = raw.get(name)
    if not isinstance(section, Mapping):
        raise KeyError(name)
    return section


def _as_bool(value: object) -> bool:
    """YAML gives real booleans, the environment gives strings: accept both."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "on", "1"}:
        return True
    if text in {"false", "no", "off", "0"}:
        return False
    raise ValueError(f"{value!r} не є логічним значенням (true/false)")


def _path(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"шлях має бути непорожнім рядком, отримано {value!r}")
    return base / value          # an absolute value simply wins over base


def _optional_path(base: Path, section: Mapping[str, Any], key: str) -> Path | None:
    return None if section.get(key) is None else _path(base, section[key])


def build_config(raw: Mapping[str, Any], base_dir: Path) -> AppConfig:
    """dict -> dataclasses. A missing key or a wrong type becomes one ConfigurationError with the cause attached."""
    try:
        input_ = _section(raw, "input")
        output = _section(raw, "output")
        processing = _section(raw, "processing")
        logging_ = _section(raw, "logging")
        return AppConfig(
            version=int(raw["version"]),
            input_path=_path(base_dir, input_["path"]),
            output=OutputConfig(
                path=_path(base_dir, output["path"]),
                errors_path=_optional_path(base_dir, output, "errors_path"),
                summary_path=_optional_path(base_dir, output, "summary_path"),
                backup=_as_bool(output.get("backup", False)),
            ),
            processing=ProcessingConfig(
                minimum_grade=float(processing["minimum_grade"]),
                skip_invalid=_as_bool(processing["skip_invalid"]),
                progress_every=int(processing.get("progress_every", 0)),
            ),
            logging=LoggingConfig(
                level=str(logging_["level"]).upper(),
                path=_path(base_dir, logging_["path"]),
                max_bytes=int(logging_.get("max_bytes", 1_000_000)),
                backup_count=int(logging_.get("backup_count", 3)),
            ),
        )
    except KeyError as error:
        raise ConfigurationError(f"у конфігурації бракує ключа {error.args[0]!r}") from error
    except (TypeError, ValueError) as error:
        raise ConfigurationError(f"некоректне значення в конфігурації: {error}") from error


def validate_config(config: AppConfig) -> None:
    """Everything that can be checked before the long import is checked here, so a typo fails in a millisecond."""
    if config.version != SCHEMA_VERSION:
        raise ConfigurationError(f"версія схеми конфігурації {config.version} не підтримується (очікую {SCHEMA_VERSION})")
    minimum = config.processing.minimum_grade
    if not GRADE_MIN <= minimum <= GRADE_MAX:
        raise ConfigurationError(f"minimum_grade має бути в межах {GRADE_MIN:g}..{GRADE_MAX:g}, отримано {minimum:g}")
    if config.processing.progress_every < 0:
        raise ConfigurationError("progress_every не може бути від'ємним")
    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"невідомий рівень логування {config.logging.level!r}; допустимі: {', '.join(sorted(LOG_LEVELS))}")
    if config.logging.max_bytes <= 0 or config.logging.backup_count < 0:
        raise ConfigurationError("logging.max_bytes має бути додатним, backup_count — невід'ємним")
    if not config.input_path.is_file():
        raise ConfigurationError(f"вхідний файл не знайдено: {config.input_path}")
    if not config.output.path.parent.is_dir():
        raise ConfigurationError(f"каталог для результату не існує: {config.output.path.parent}")


def load_config(path: Path, *, environ: Mapping[str, str] | None = None) -> AppConfig:
    """Read -> override from the environment -> build -> validate. `environ` is injectable for tests and demos."""
    raw = read_yaml_mapping(path)
    apply_env_overrides(raw, os.environ if environ is None else environ)
    config = build_config(raw, path.parent)
    validate_config(config)
    return config
