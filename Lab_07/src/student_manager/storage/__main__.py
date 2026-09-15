"""Entry point of the storage package.

    python -m student_manager.storage                       deterministic demo, files under data/
    python -m student_manager.storage run -c config.yaml    one configured import/export run; exit code 1 on failure
    python -m student_manager.storage experiments           strict/tolerant and eager/streaming measurements
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from student_manager.analytics.data import load_records
from student_manager.registry import StudentRegistry
from student_manager.storage import benchmark
from student_manager.storage.config import AppConfig, load_config
from student_manager.storage.context import open_text
from student_manager.storage.dataset import DEMO_CONFIG, write_demo_config, write_students_csv
from student_manager.storage.dto import Row
from student_manager.storage.exceptions import ConfigurationError, DataError, DataExportError, RecordValidationError, StorageError
from student_manager.storage.exporters import write_rows
from student_manager.storage.logging_config import configure_logging, reset_logging
from student_manager.storage.readers import read_rows
from student_manager.storage.services import STRICT, ImportStatistics, export_grade_records, import_grade_records, run_pipeline
from student_manager.storage.validators import parse_student_row, to_student

logger = logging.getLogger("student_manager.storage.main")

# Experiment 5: six broken configurations, each a small edit of the demo YAML.
BROKEN_CONFIGS: list[tuple[str, str | None]] = [
    ("відсутній config.yaml", None),
    ("неправильний YAML", "version: 1\ninput: [unclosed\n"),
    ("немає ключа input", DEMO_CONFIG.replace("input:\n  path: students.csv\n", "")),
    ("minimum_grade = 150", DEMO_CONFIG.replace("minimum_grade: 80", "minimum_grade: 150")),
    ("input file відсутній", DEMO_CONFIG.replace("path: students.csv", "path: missing.csv")),
    ("output directory не існує", DEMO_CONFIG.replace("path: output/students.json", "path: nowhere/students.json")),
]


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def head(path: Path, lines: int = 8) -> str:
    with open_text(path, "r") as file:
        text = file.read().splitlines()
    shown = text[:lines]
    if len(text) > lines:
        shown.append(f"... (ще {len(text) - lines} рядків)")
    return "\n".join(f"  {line}" for line in shown)


def describe(config: AppConfig, base: Path) -> None:
    def rel(path: Path | None) -> str:
        if path is None:
            return "-"
        return str(path.relative_to(base)) if path.is_relative_to(base) else str(path)

    print(f"  version={config.version}  input={rel(config.input_path)}")
    print(f"  output: path={rel(config.output.path)}  errors_path={rel(config.output.errors_path)}  "
          f"summary_path={rel(config.output.summary_path)}  backup={config.output.backup}")
    print(f"  processing: minimum_grade={config.processing.minimum_grade:g}  "
          f"skip_invalid={config.processing.skip_invalid}  progress_every={config.processing.progress_every}")
    print(f"  logging: level={config.logging.level}  path={rel(config.logging.path)}  "
          f"max_bytes={config.logging.max_bytes}  backup_count={config.logging.backup_count}")


def run(config_path: Path, *, console: TextIO | None = None) -> int:
    """The 'real' application: exit code 0 on success, 1 on any StorageError, never a raw traceback for the user."""
    try:
        config = load_config(config_path)
        configure_logging(config.logging.level, config.logging.path, max_bytes=config.logging.max_bytes,
                          backup_count=config.logging.backup_count, console=console)
        result = run_pipeline(config)
    except StorageError as error:
        cause = f" (причина: {type(error.__cause__).__name__}: {error.__cause__})" if error.__cause__ else ""
        logger.error("критична помилка: %s%s", error, cause)
        return 1
    print(f"Готово: {result.statistics}, exported={result.exported} -> {result.output_path}")
    return 0


def rows_then_disk_failure() -> Iterator[Row]:
    """Two good records, then the kind of OSError a full disk raises in the middle of an export."""
    yield {"student_id": 1, "name": "Гнатишин Марта", "group": "ФЕП-31с", "grade": 93.25, "email": "marta.hnatyshyn@lnu.edu.ua"}
    yield {"student_id": 3, "name": "Вовк Тарас", "group": "ФЕП-31с", "grade": 85.0, "email": "taras.vovk@lnu.edu.ua"}
    raise OSError(28, "No space left on device (імітація)")


def demo(data_dir: Path) -> None:
    data_dir = data_dir.resolve()
    output_dir = data_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    show("1. ПІДГОТОВКА: config.yaml і students.csv (pathlib, текстові файли)")
    config_path = write_demo_config(data_dir / "config.yaml")
    csv_path = write_students_csv(data_dir / "students.csv")
    print(f"  {config_path.name}: {config_path.stat().st_size} байт, {csv_path.name}: {csv_path.stat().st_size} байт")
    print(head(csv_path, 20))

    show("2. КОНФІГУРАЦІЯ: load_config -> AppConfig (YAML, frozen dataclasses, валідація)")
    config = load_config(config_path)
    describe(config, data_dir)
    overridden = load_config(config_path, environ={"STUDENT_MANAGER_MINIMUM_GRADE": "90", "STUDENT_MANAGER_SKIP_INVALID": "no"})
    print(f"  з environment (MINIMUM_GRADE=90, SKIP_INVALID=no): minimum_grade={overridden.processing.minimum_grade:g}, "
          f"skip_invalid={overridden.processing.skip_invalid}")

    show("3. LOGGING: RotatingFileHandler + консоль, рівень із конфігурації")
    configure_logging(config.logging.level, config.logging.path, max_bytes=config.logging.max_bytes,
                      backup_count=config.logging.backup_count, console=sys.stdout)
    print(f"  журнал: {config.logging.path.relative_to(data_dir)}")

    show("4. TOLERANT MODE: CSV -> валідація -> фільтр minimum_grade -> атомарний JSON + errors.csv + summary.json")
    result = run_pipeline(config)
    print(f"  статистика: {result.statistics}, за полями {dict(result.statistics.invalid_by_field)}")
    print(f"  {config.output.path.name} ({result.exported} записів):")
    print(head(config.output.path, 14))
    assert config.output.errors_path is not None and config.output.summary_path is not None
    print(f"  {config.output.errors_path.name}:")
    print(head(config.output.errors_path, 3))
    summary = json.loads(config.output.summary_path.read_text("utf-8"))
    print(f"  {config.output.summary_path.name}: statistics={summary['statistics']}, exported={summary['exported']}")

    show("5. ДОМЕННА МОДЕЛЬ: students.json -> StudentRow -> Student -> StudentRegistry (ЛР1)")
    registry = StudentRegistry(to_student(parse_student_row(row, n)) for n, row in read_rows(config.output.path))
    best = registry.best()
    print(f"  зареєстровано {len(registry)}; найкращий: {best.full_name} ({best.group}, {best.average_grade:.2f})")
    for group in registry.groups():
        print(f"  {group}: {len(registry.by_group(group))} студ., середній бал {registry.group_average(group):.2f}")

    show("6. STRICT MODE: перша помилка зупиняє імпорт, попередній результат не чіпається")
    strict_config = load_config(write_demo_config(data_dir / "config_strict.yaml", skip_invalid=False))
    before = config.output.path.read_bytes()
    try:
        run_pipeline(strict_config)
    except RecordValidationError as error:
        print(f"  {type(error).__name__}: {error} ({error.location})")
    print(f"  students.json незмінний: {config.output.path.read_bytes() == before}; "
          f"тимчасові файли: {[p.name for p in output_dir.glob('*.tmp')] or 'немає'}")

    show("7. EXCEPTION CHAINING: ValueError -> RecordValidationError (експеримент 3)")
    bad_row: Row = {"student_id": "1", "name": "Литвин Андрій", "group": "ФЕП-31с", "grade": "wrong", "email": "andrii.lytvyn@lnu.edu.ua"}
    try:
        parse_student_row(bad_row, 2)
    except RecordValidationError as error:
        print(f"  {type(error).__name__}: {error}\n  __cause__ = {error.__cause__!r}\n  traceback:")
        traceback.print_exc(file=sys.stdout)
    try:
        parse_student_row({**bad_row, "grade": "79", "group": "31с"}, 3)
    except RecordValidationError as error:
        print(f"  {type(error).__name__} <- {type(error.__cause__).__name__} (модель ЛР1): {error}")

    show("8. ATOMIC OUTPUT: збій посеред експорту (експеримент 4), потім успішний експорт із backup")
    before = config.output.path.read_bytes()
    try:
        write_rows(rows_then_disk_failure(), config.output.path, backup=True)
    except DataExportError as error:
        print(f"  {type(error).__name__}: {error}\n  __cause__ = {error.__cause__!r}")
    tmp, bak = config.output.path.with_name("students.json.tmp"), config.output.path.with_name("students.json.bak")
    print(f"  students.json незмінний: {config.output.path.read_bytes() == before}; .tmp існує: {tmp.exists()}; .bak існує: {bak.exists()}")
    rows = [row for _, row in read_rows(config.output.path)]
    write_rows(rows, config.output.path, backup=True)
    print(f"  повторний експорт {len(rows)} записів із backup=True: .bak існує: {bak.exists()}, збігається з попереднім: {bak.read_bytes() == before}")

    show("9. ПОМИЛКИ КОНФІГУРАЦІЇ: fail-fast (експеримент 5)")
    for number, (title, text) in enumerate(BROKEN_CONFIGS, start=1):
        path = data_dir / f"broken_{number}.yaml"
        if text is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(text, encoding="utf-8")
        try:
            load_config(path)
        except ConfigurationError as error:
            cause = f"  <- {type(error.__cause__).__name__}" if error.__cause__ else ""
            print(f"  {number}. {title:<27} ConfigurationError: {error}{cause}")
    print(f"  run(broken_1.yaml) -> exit code {run(data_dir / 'broken_1.yaml')}")

    show("10. ФОРМАТИ: GradeRecord (ЛР2) -> CSV / JSON Lines / YAML / JSON.gz -> назад (Importer/Exporter Protocol)")
    records = load_records()
    for name in ("grades.csv", "grades.jsonl", "grades.yaml", "grades.json.gz"):
        path = output_dir / name
        written = export_grade_records(records, path)
        statistics = ImportStatistics()
        back = list(import_grade_records(path, policy=STRICT, statistics=statistics))
        print(f"  {name:<14} записано {written}, прочитано {len(back)}, {path.stat().st_size:>5} байт, "
              f"збігається з оригіналом: {back == records}")
    print("  grades.jsonl:")
    print(head(output_dir / "grades.jsonl", 2))
    print("  grades.yaml:")
    print(head(output_dir / "grades.yaml", 4))

    show("11. ПОШКОДЖЕНІ ФАЙЛИ: DataImportError із збереженою причиною")
    (data_dir / "broken.json").write_text('[{"student": "Гнатишин Марта", "group": "ФЕП-31с", "discipline": "Мова С", "grade": 91}, {"student": ', "utf-8")
    (data_dir / "broken.yaml").write_text("- student: Гнатишин Марта\n  grade: [91, 92\n", "utf-8")
    (data_dir / "wrong_header.csv").write_text("id,name\n1,x\n", "utf-8")
    for path in (data_dir / "broken.json", data_dir / "broken.yaml", data_dir / "wrong_header.csv",
                 data_dir / "missing.csv", data_dir / "grades.xml"):
        try:
            list(import_grade_records(path, policy=STRICT, statistics=ImportStatistics()))
        except DataError as error:
            cause = f"\n  {'':16} <- {type(error.__cause__).__name__}: {error.__cause__}" if error.__cause__ else ""
            print(f"  {path.name:<16} {type(error).__name__}: {error}{cause}")

    show("12. ФРАГМЕНТ LOG-ФАЙЛУ")
    reset_logging()
    lines = config.logging.path.read_text("utf-8").splitlines()
    print(f"  {config.logging.path.relative_to(data_dir)}: {len(lines)} рядків, останні 10:")
    print("\n".join(f"  {line}" for line in lines[-10:]))


def experiments(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging("INFO", data_dir / "logs" / "experiments.log")
    show("ЕКСПЕРИМЕНТ 1: strict vs tolerant (1 000 valid + 10 invalid записів)")
    print(benchmark.format_policy_table(benchmark.strict_vs_tolerant(data_dir)))
    show("ЕКСПЕРИМЕНТ 2: eager vs streaming, час і peak memory (tracemalloc)")
    print(benchmark.format_memory_table(benchmark.eager_vs_streaming(data_dir)))
    reset_logging()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m student_manager.storage", description="Імпорт/експорт і конфігурація (ЛР5)")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="каталог для файлів демонстрації (типово data/)")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("demo", help="детермінована демонстрація (типово)")
    run_parser = commands.add_parser("run", help="один запуск pipeline за конфігурацією")
    run_parser.add_argument("-c", "--config", type=Path, required=True, help="шлях до config.yaml")
    commands.add_parser("experiments", help="експерименти strict/tolerant та eager/streaming")
    return parser


def main(argv: list[str] | None = None) -> None:
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.command == "run":
        raise SystemExit(run(args.config, console=sys.stderr))
    if args.command == "experiments":
        experiments(args.data_dir)
    else:
        demo(args.data_dir)


if __name__ == "__main__":
    main()
