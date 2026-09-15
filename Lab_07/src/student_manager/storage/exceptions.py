"""Storage-layer exceptions. Every one of them is a StudentManagerError, so code that already catches
the project base class keeps working; new code can be as specific as it needs.

    StudentManagerError                 (student_manager.exceptions, lab 1)
    └── StorageError
        ├── ConfigurationError          config file missing / malformed / fails validation
        └── DataError
            ├── DataImportError         input cannot be opened or parsed
            ├── DataExportError         output cannot be written (old output stays intact)
            ├── UnsupportedFormatError  extension maps to no known format
            └── RecordValidationError   one record is wrong; knows the line and the field
"""

from __future__ import annotations

from pathlib import Path

from student_manager.exceptions import StudentManagerError


class StorageError(StudentManagerError):
    """Base class for import, export and configuration failures."""


class ConfigurationError(StorageError):
    """The configuration is missing, malformed or does not pass validation (fail-fast, before any work)."""


class DataError(StorageError):
    """Base class for problems with the data itself."""


class DataImportError(DataError):
    """Input cannot be read or parsed: missing file, broken CSV/JSON/YAML, wrong header."""


class DataExportError(DataError):
    """Output cannot be written. The previous output file, if any, is left untouched."""


class UnsupportedFormatError(DataError):
    """File extension does not map to a known format."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"невідомий формат файлу {path.name!r}: очікую .csv, .json, .jsonl, .yaml (можна з .gz)")
        self.path = path


class RecordValidationError(DataError):
    """One record failed validation. Remembers where (line) and what (field) for the log and the error CSV."""

    def __init__(self, message: str, *, line_number: int | None = None, field: str | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field

    @property
    def location(self) -> str:
        """'рядок 12, поле grade' — for log messages and the error report."""
        where = "рядок ?" if self.line_number is None else f"рядок {self.line_number}"
        return f"{where}, поле {self.field}" if self.field else where
