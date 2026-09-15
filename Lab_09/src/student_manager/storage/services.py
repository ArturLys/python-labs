"""The pipeline: config -> streaming import -> validation under a strict/tolerant policy -> filtering
-> atomic export -> summary. Nothing here touches a file directly; readers, exporters and context do."""

from __future__ import annotations

import csv
import logging
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import TypeVar

from student_manager.analytics.data import GradeRecord
from student_manager.storage.config import AppConfig, ProcessingConfig
from student_manager.storage.context import AtomicWriter, logged_operation
from student_manager.storage.dto import GRADE_FIELDS, STUDENT_FIELDS, Row, StudentRow, grade_record_to_dict
from student_manager.storage.exceptions import RecordValidationError
from student_manager.storage.exporters import to_json, write_rows
from student_manager.storage.readers import read_rows
from student_manager.storage.validators import parse_grade_record, parse_student_row

logger = logging.getLogger(__name__)

T = TypeVar("T")
InvalidCallback = Callable[[RecordValidationError, Row], None]
ERROR_FIELDS: tuple[str, ...] = ("line", "field", "message", "raw")


@dataclass(slots=True)
class ImportStatistics:
    """Counters that the streaming import updates in place while the consumer pulls records."""

    total: int = 0
    valid: int = 0
    invalid: int = 0
    invalid_by_field: Counter[str] = field(default_factory=Counter)

    def note_invalid(self, error: RecordValidationError) -> None:
        self.invalid += 1
        self.invalid_by_field[error.field or "?"] += 1

    def as_dict(self) -> dict[str, object]:
        return {"total": self.total, "valid": self.valid, "invalid": self.invalid,
                "invalid_by_field": dict(self.invalid_by_field)}

    def __str__(self) -> str:
        return f"total={self.total} valid={self.valid} invalid={self.invalid}"


@dataclass(frozen=True, slots=True)
class ImportPolicy:
    """What happens to an invalid record: strict aborts on the first one, tolerant logs, counts and skips."""

    skip_invalid: bool
    progress_every: int = 0

    @property
    def mode(self) -> str:
        return "tolerant" if self.skip_invalid else "strict"

    @classmethod
    def from_config(cls, processing: ProcessingConfig) -> ImportPolicy:
        return cls(skip_invalid=processing.skip_invalid, progress_every=processing.progress_every)


STRICT = ImportPolicy(skip_invalid=False)
TOLERANT = ImportPolicy(skip_invalid=True)


def import_records(path: Path, parse: Callable[[Row, int], T], *, required: tuple[str, ...],
                   policy: ImportPolicy, statistics: ImportStatistics,
                   on_invalid: InvalidCallback | None = None) -> Iterator[T]:
    """Generic streaming import: one raw row in, one validated object out, never the whole file.

    try/except/else: the parser may raise, the policy decides, `else` counts and yields only the good ones.
    In strict mode a bare `raise` re-raises the very same exception with its chain intact.
    """
    logger.info("імпорт %s, режим %s", path.name, policy.mode)
    for line_number, raw in read_rows(path, required=required):
        statistics.total += 1
        if policy.progress_every and statistics.total % policy.progress_every == 0:
            logger.info("прочитано %d записів", statistics.total)
        try:
            record = parse(raw, line_number)
        except RecordValidationError as error:
            statistics.note_invalid(error)
            logger.warning("некоректний запис (%s): %s", error.location, error)
            if on_invalid is not None:
                on_invalid(error, raw)
            if policy.skip_invalid:
                continue
            raise
        else:
            statistics.valid += 1
            yield record


def import_students(path: Path, *, policy: ImportPolicy, statistics: ImportStatistics,
                    on_invalid: InvalidCallback | None = None) -> Iterator[StudentRow]:
    return import_records(path, parse_student_row, required=STUDENT_FIELDS, policy=policy,
                          statistics=statistics, on_invalid=on_invalid)


def import_grade_records(path: Path, *, policy: ImportPolicy, statistics: ImportStatistics) -> Iterator[GradeRecord]:
    return import_records(path, parse_grade_record, required=GRADE_FIELDS, policy=policy, statistics=statistics)


def export_grade_records(records: Iterable[GradeRecord], path: Path, *, backup: bool = False) -> int:
    return write_rows((grade_record_to_dict(r) for r in records), path, backup=backup, fieldnames=GRADE_FIELDS)


def filter_by_grade(rows: Iterable[StudentRow], minimum_grade: float) -> Iterator[StudentRow]:
    """A generator expression, so it slots into the stream without collecting anything."""
    return (row for row in rows if row.grade >= minimum_grade)


@contextmanager
def error_report(path: Path) -> Iterator[InvalidCallback]:
    """Collect rejected rows into a separate CSV (line, field, message, raw row). Atomic like every output:
    if the run is aborted, the report is not left half-written either."""
    with AtomicWriter(path) as file:
        writer = csv.DictWriter(file, fieldnames=ERROR_FIELDS)
        writer.writeheader()

        def record(error: RecordValidationError, raw: Row) -> None:
            writer.writerow({"line": error.line_number, "field": error.field, "message": str(error),
                             "raw": to_json(raw)})

        yield record


@dataclass(frozen=True, slots=True)
class PipelineResult:
    statistics: ImportStatistics
    exported: int
    output_path: Path
    elapsed: float


def write_summary(path: Path, config: AppConfig, result: PipelineResult) -> None:
    """Machine-readable report of the run next to the output (paths serialised by StorageJSONEncoder)."""
    payload = {
        "config": asdict(config),
        "statistics": result.statistics.as_dict(),
        "exported": result.exported,
        "elapsed_seconds": round(result.elapsed, 3),
    }
    with AtomicWriter(path) as file:
        file.write(to_json(payload, pretty=True) + "\n")


def run_pipeline(config: AppConfig) -> PipelineResult:
    """One configured run. `finally` logs the counters even when strict mode aborts half-way."""
    statistics = ImportStatistics()
    policy = ImportPolicy.from_config(config.processing)
    exported = 0
    start = perf_counter()
    errors: AbstractContextManager[InvalidCallback | None] = (
        nullcontext(None) if config.output.errors_path is None else error_report(config.output.errors_path)
    )
    try:
        with logged_operation("імпорт/експорт студентів"), errors as on_invalid:
            rows = import_students(config.input_path, policy=policy, statistics=statistics, on_invalid=on_invalid)
            selected = filter_by_grade(rows, config.processing.minimum_grade)
            exported = write_rows((row.to_dict() for row in selected), config.output.path,
                                  backup=config.output.backup, fieldnames=STUDENT_FIELDS)
    finally:
        logger.info("підсумок: %s exported=%d (minimum_grade=%g, режим %s)",
                    statistics, exported, config.processing.minimum_grade, policy.mode)
    result = PipelineResult(statistics, exported, config.output.path, perf_counter() - start)
    if config.output.summary_path is not None:
        write_summary(config.output.summary_path, config, result)
    return result
