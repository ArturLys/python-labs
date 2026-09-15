"""Logging setup driven by the configuration: a rotating file under data/ or logs/, plus an optional console stream."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str, path: Path, *, max_bytes: int = 1_000_000, backup_count: int = 3,
                      console: TextIO | None = None) -> logging.Logger:
    """(Re)configure the root logger.

    force=True closes and replaces the previous handlers, so a second call in the same process (tests,
    the demo) does not duplicate every line. The log directory is created on demand: a missing logs/
    is not a reason to refuse to run, unlike a missing input file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"),
    ]
    if console is not None:
        handlers.append(logging.StreamHandler(console))
    logging.basicConfig(level=logging.getLevelNamesMapping()[level.upper()], format=LOG_FORMAT,
                        datefmt=DATE_FORMAT, handlers=handlers, force=True)
    logger = logging.getLogger("student_manager.storage")
    logger.debug("logging: рівень %s, файл %s", level.upper(), path)
    return logger


def reset_logging() -> None:
    """Close every root handler (releases the log file on Windows). Used by tests and at the end of the demo."""
    logging.basicConfig(handlers=[], force=True)
