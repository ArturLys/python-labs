"""Source stage: the same streaming line reader as a generator and as hand-written iterable/iterator classes."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import IO


def read_lines(path: Path) -> Generator[str, None, None]:
    """Generator: the file is opened on the first next() and stays open only while lines are being pulled.

    Annotated as Generator rather than Iterator so that callers may close() it and release the file early.
    """
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from file


class LineReader:
    """Iterator over the lines of a file: __iter__ returns self, __next__ pulls one line, StopIteration closes it.

    read_lines() does the same in three lines. The class exists to show the protocol without magic and to
    expose `lines_read`, which lets the caller see how far an early-terminated pipeline actually got.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lines_read = 0
        self._file: IO[str] | None = None
        self._done = False

    def __iter__(self) -> LineReader:
        return self

    def __next__(self) -> str:
        if self._done:
            raise StopIteration
        if self._file is None:
            self._file = self.path.open("r", encoding="utf-8", newline="")
        line = self._file.readline()
        if not line:
            self.close()
            raise StopIteration
        self.lines_read += 1
        return line

    def close(self) -> None:
        """Release the file; after this the iterator is exhausted for good (one-shot)."""
        self._done = True
        if self._file is not None:
            self._file.close()
            self._file = None

    @property
    def closed(self) -> bool:
        return self._file is None


class CsvDataset:
    """Iterable container: every iter() hands out a fresh LineReader, so the file can be walked again and again."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __iter__(self) -> LineReader:
        return LineReader(self.path)

    def __repr__(self) -> str:
        return f"CsvDataset({self.path.name!r})"
