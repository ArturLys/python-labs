"""Exporters: dict rows out to CSV, JSON, JSON Lines or YAML through one Exporter protocol.

Every writer goes through AtomicWriter, so a failure in the middle never leaves a half-written file,
and every writer consumes its rows lazily - even the JSON array is emitted record by record.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from textwrap import indent
from typing import Any, Protocol

import yaml

from student_manager.storage.context import AtomicWriter
from student_manager.storage.dto import Row
from student_manager.storage.exceptions import DataExportError
from student_manager.storage.readers import Format, detect_format


class StorageJSONEncoder(json.JSONEncoder):
    """json.dumps cannot serialise Path, dataclasses, sets or datetimes; this teaches it the four."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Path):
            return str(o)
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        if isinstance(o, datetime):
            return o.isoformat(timespec="seconds")
        return super().default(o)


def to_json(value: object, *, pretty: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, cls=StorageJSONEncoder)


class Exporter(Protocol):
    def write(self, rows: Iterable[Row], path: Path) -> int: ...


class JsonExporter:
    """A JSON array written as '[', one object per record, ']' - the list itself is never built."""

    def __init__(self, *, backup: bool = False) -> None:
        self.backup = backup

    def write(self, rows: Iterable[Row], path: Path) -> int:
        count = 0
        try:
            with AtomicWriter(path, backup=self.backup) as file:
                file.write("[\n")
                for row in rows:
                    if count:
                        file.write(",\n")
                    file.write(indent(to_json(row, pretty=True), "  "))
                    count += 1
                file.write("\n]\n")
        except OSError as error:
            raise DataExportError(f"не вдалося записати {path}") from error
        except (TypeError, ValueError) as error:
            raise DataExportError(f"{path.name}: запис {count + 1} не серіалізується в JSON — {error}") from error
        return count


class JsonLinesExporter:
    """One compact JSON object per line: streams both ways."""

    def __init__(self, *, backup: bool = False) -> None:
        self.backup = backup

    def write(self, rows: Iterable[Row], path: Path) -> int:
        count = 0
        try:
            with AtomicWriter(path, backup=self.backup) as file:
                for row in rows:
                    file.write(to_json(row) + "\n")
                    count += 1
        except OSError as error:
            raise DataExportError(f"не вдалося записати {path}") from error
        except (TypeError, ValueError) as error:
            raise DataExportError(f"{path.name}: запис {count + 1} не серіалізується в JSON — {error}") from error
        return count


class CsvExporter:
    """csv.DictWriter. The header comes from `fieldnames` or, if not given, from the first row."""

    def __init__(self, fieldnames: Sequence[str] | None = None, *, backup: bool = False) -> None:
        self.fieldnames = fieldnames
        self.backup = backup

    def write(self, rows: Iterable[Row], path: Path) -> int:
        count = 0
        try:
            with AtomicWriter(path, backup=self.backup) as file:
                writer: csv.DictWriter[str] | None = None
                for row in rows:
                    if writer is None:
                        writer = csv.DictWriter(file, fieldnames=self.fieldnames or list(row))
                        writer.writeheader()
                    writer.writerow(row)
                    count += 1
                if writer is None and self.fieldnames:          # no rows at all: still a valid file with a header
                    csv.DictWriter(file, fieldnames=self.fieldnames).writeheader()
        except OSError as error:
            raise DataExportError(f"не вдалося записати {path}") from error
        except ValueError as error:                              # DictWriter: a key that is not in fieldnames
            raise DataExportError(f"{path.name}: запис {count + 1} не відповідає заголовку — {error}") from error
        return count


class YamlExporter:
    """Each record is dumped as a one-element sequence ('- key: value'); concatenated they are one valid
    YAML list, so this streams as well instead of building the whole document first."""

    def __init__(self, *, backup: bool = False) -> None:
        self.backup = backup

    def write(self, rows: Iterable[Row], path: Path) -> int:
        count = 0
        try:
            with AtomicWriter(path, backup=self.backup) as file:
                for row in rows:
                    yaml.safe_dump([row], file, allow_unicode=True, sort_keys=False)
                    count += 1
                if not count:
                    file.write("[]\n")
        except OSError as error:
            raise DataExportError(f"не вдалося записати {path}") from error
        except yaml.YAMLError as error:                          # RepresenterError: a value YAML cannot express
            raise DataExportError(f"{path.name}: запис {count + 1} не серіалізується в YAML — {error}") from error
        return count


def exporter_for(path: Path, *, backup: bool = False, fieldnames: Sequence[str] | None = None) -> Exporter:
    """Pick the implementation by extension (.gz is handled inside AtomicWriter)."""
    fmt = detect_format(path)
    if fmt is Format.CSV:
        return CsvExporter(fieldnames, backup=backup)
    exporters: dict[Format, Exporter] = {
        Format.JSON: JsonExporter(backup=backup),
        Format.JSONL: JsonLinesExporter(backup=backup),
        Format.YAML: YamlExporter(backup=backup),
    }
    return exporters[fmt]


def write_rows(rows: Iterable[Row], path: Path, *, backup: bool = False,
               fieldnames: Sequence[str] | None = None) -> int:
    """The single entry point of the output side. Returns the number of records written."""
    return exporter_for(path, backup=backup, fieldnames=fieldnames).write(rows, path)
