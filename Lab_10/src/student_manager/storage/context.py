"""Hand-written context managers: a transaction-like atomic file write (class with __enter__/__exit__)
and a logged, timed operation (generator + contextlib.contextmanager). Also the one place that opens
text files, so encoding and gzip are decided once."""

from __future__ import annotations

import gzip
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from types import TracebackType
from typing import Literal, TextIO

from student_manager.storage.exceptions import DataExportError

logger = logging.getLogger(__name__)

Mode = Literal["r", "w"]


def open_text(path: Path, mode: Mode = "r", *, compressed: bool | None = None) -> TextIO:
    """UTF-8 text stream, newline='' so csv gets raw line endings; gzip when the name ends with .gz."""
    if compressed is None:
        compressed = path.suffix == ".gz"
    if not compressed:
        return path.open(mode, encoding="utf-8", newline="")
    if mode == "r":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return gzip.open(path, "wt", encoding="utf-8", newline="")


class AtomicWriter:
    """Write to <name>.tmp; on success the temp file replaces the target in one os.replace() call, on
    failure it is deleted and the previous output is never touched. Optionally keeps the old file as .bak.

        with AtomicWriter(path, backup=True) as file:
            file.write(...)          # any exception here -> no half-written output
    """

    def __init__(self, path: Path, *, backup: bool = False) -> None:
        self.path = path
        self.backup = backup
        self.temporary = path.with_name(path.name + ".tmp")
        self._file: TextIO | None = None

    def __enter__(self) -> TextIO:
        try:
            self._file = open_text(self.temporary, "w", compressed=self.path.suffix == ".gz")
        except OSError as error:
            raise DataExportError(f"не вдалося створити тимчасовий файл {self.temporary}") from error
        return self._file

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Returns None (falsy), so the caller's exception is never swallowed."""
        if self._file is not None:
            self._file.close()
        if exc_type is not None:
            self.temporary.unlink(missing_ok=True)
            logger.warning(
                "запис %s перервано (%s): тимчасовий файл видалено, попередній результат збережено",
                self.path.name,
                exc_type.__name__,
            )
            return
        try:
            if self.backup and self.path.exists():
                self.path.replace(self.path.with_name(self.path.name + ".bak"))
            self.temporary.replace(self.path)
        except OSError as error:
            self.temporary.unlink(missing_ok=True)
            raise DataExportError(f"не вдалося замінити {self.path} новим файлом") from error


@contextmanager
def logged_operation(name: str, *, log: logging.Logger = logger) -> Iterator[None]:
    """Log the start, then either the success with the elapsed time or the failure with its traceback.

    The code before `yield` is __enter__, the code after it is __exit__; the exception raised inside
    the with-block shows up right at the yield, which is why the try/except wraps it.
    """
    log.info("%s: початок", name)
    start = perf_counter()
    try:
        yield
    except Exception:
        log.exception("%s: перервано через помилку після %.3f с", name, perf_counter() - start)
        raise
    else:
        log.info("%s: завершено за %.3f с", name, perf_counter() - start)
