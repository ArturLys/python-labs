"""Importers: CSV, JSON Lines, JSON array and YAML behind one Importer protocol, chosen by extension.

CSV and JSON Lines stream (one record in memory at a time). A JSON array or a YAML document has to be
parsed whole - json.load() and yaml.safe_load() have no streaming mode - so those two are for
configuration-sized files; for big data use .csv or .jsonl (optionally .gz).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import yaml

from student_manager.storage.context import open_text
from student_manager.storage.dto import Row
from student_manager.storage.exceptions import DataImportError, UnsupportedFormatError

# (line number for text formats / record position for JSON and YAML, the raw record)
NumberedRow = tuple[int, Row]


class Format(StrEnum):
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    YAML = "yaml"


SUFFIXES: dict[str, Format] = {
    ".csv": Format.CSV, ".json": Format.JSON, ".jsonl": Format.JSONL, ".yaml": Format.YAML, ".yml": Format.YAML,
}


def detect_format(path: Path) -> Format:
    """students.csv -> CSV, grades.jsonl.gz -> JSONL: the .gz layer is transparent."""
    name = path.with_suffix("") if path.suffix == ".gz" else path
    try:
        return SUFFIXES[name.suffix.lower()]
    except KeyError as error:
        raise UnsupportedFormatError(path) from error


class Importer(Protocol):
    """Structural interface: anything with read(path) -> iterator of numbered rows is an Importer."""

    def read(self, path: Path) -> Iterator[NumberedRow]: ...


def _as_row(value: object, path: Path, position: int) -> Row:
    if not isinstance(value, dict):
        raise DataImportError(f"{path.name}, запис {position}: очікую об'єкт (mapping), а не {type(value).__name__}")
    return {str(key): item for key, item in value.items()}


def _numbered(data: object, path: Path) -> Iterator[NumberedRow]:
    if not isinstance(data, list):
        raise DataImportError(f"{path.name}: очікую список записів, а не {type(data).__name__}")
    for position, item in enumerate(data, start=1):
        yield position, _as_row(item, path, position)


class CsvImporter:
    """csv.DictReader row by row; the file is never fully in memory. The header is checked first (fail-fast)."""

    def __init__(self, required: tuple[str, ...] = ()) -> None:
        self.required = required

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with open_text(path, "r") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    raise DataImportError(f"{path.name}: порожній файл, немає рядка заголовка")
                missing = [name for name in self.required if name not in reader.fieldnames]
                if missing:
                    raise DataImportError(f"{path.name}: у заголовку бракує колонок {', '.join(missing)}")
                for row in reader:
                    yield reader.line_num, row
        except OSError as error:
            raise DataImportError(f"не вдалося прочитати {path}") from error
        except csv.Error as error:
            raise DataImportError(f"{path.name}: пошкоджений CSV — {error}") from error


class JsonLinesImporter:
    """One JSON object per line: streams like CSV, but numbers stay numbers."""

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with open_text(path, "r") as file:
                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise DataImportError(f"{path.name}, рядок {line_number}: некоректний JSON — {error.msg}") from error
                    yield line_number, _as_row(value, path, line_number)
        except OSError as error:
            raise DataImportError(f"не вдалося прочитати {path}") from error


class JsonImporter:
    """A whole JSON array; positions instead of line numbers."""

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with open_text(path, "r") as file:
                data = json.load(file)
        except OSError as error:
            raise DataImportError(f"не вдалося прочитати {path}") from error
        except json.JSONDecodeError as error:
            raise DataImportError(f"{path.name}: некоректний JSON — {error.msg} (рядок {error.lineno})") from error
        yield from _numbered(data, path)


class YamlImporter:
    """A whole YAML document through safe_load(): no arbitrary Python objects from untrusted files."""

    def read(self, path: Path) -> Iterator[NumberedRow]:
        try:
            with open_text(path, "r") as file:
                data = yaml.safe_load(file)
        except OSError as error:
            raise DataImportError(f"не вдалося прочитати {path}") from error
        except yaml.YAMLError as error:
            raise DataImportError(f"{path.name}: некоректний YAML — {str(error).splitlines()[0]}") from error
        yield from _numbered(data, path)


def importer_for(path: Path, *, required: tuple[str, ...] = ()) -> Importer:
    """Pick the implementation by extension. `required` columns are checked on the CSV header only;
    for the other formats every row is validated individually anyway."""
    fmt = detect_format(path)
    if fmt is Format.CSV:
        return CsvImporter(required)
    importers: dict[Format, Importer] = {
        Format.JSON: JsonImporter(), Format.JSONL: JsonLinesImporter(), Format.YAML: YamlImporter(),
    }
    return importers[fmt]


def read_rows(path: Path, *, required: tuple[str, ...] = ()) -> Iterator[NumberedRow]:
    """The single entry point of the input side."""
    return importer_for(path, required=required).read(path)
