"""Demo of the streaming package: `python -m student_manager.streaming` (run from the project root)."""

from __future__ import annotations

import io
import logging
import os
import sys
from contextlib import closing
from inspect import getgeneratorstate
from itertools import islice
from pathlib import Path

from student_manager.analytics.processors import count_records_by_group
from student_manager.streaming import experiment
from student_manager.streaming.aggregates import (
    by_group,
    count_by_group,
    find_first,
    grade_changes,
    running_average,
    streaming_stats,
    top_n,
)
from student_manager.streaming.batching import Nested, adaptive_batches, batched, flatten
from student_manager.streaming.experiment import fmt_int, fmt_seconds
from student_manager.streaming.filters import head_by_id, in_groups, with_min_grade
from student_manager.streaming.generate import ensure_dataset, generate_rows, student_ids
from student_manager.streaming.models import StudentRecord
from student_manager.streaming.parsers import ValidationReport, clean_lines, parse_rows
from student_manager.streaming.pipeline import assemble, build_multi_pipeline, build_pipeline, export_csv, log
from student_manager.streaming.readers import CsvDataset, LineReader, read_lines
from student_manager.streaming.transforms import to_grade_records

DATA_DIR = Path(os.environ.get("STUDENT_MANAGER_DATA", "data"))
ROWS = 200_000
MINIMUM = 85.0


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def fmt(record: StudentRecord | None) -> str:
    if record is None:
        return "None"
    return f"{record.student_id:>7}  {record.name:<22} {record.group:<8} {record.grade:5.1f}"


def is_excellent_in_33(record: StudentRecord) -> bool:
    return record.group == "ФЕП-33" and record.grade >= 99.0


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="  [log] %(message)s", stream=sys.stdout)

    path = DATA_DIR / "students.csv"
    existed = path.exists()
    ensure_dataset(path, ROWS)
    show(f"НАБІР ДАНИХ: {path} — {'знайдено' if existed else 'згенеровано'}, "
         f"{fmt_int(ROWS)} рядків, {path.stat().st_size / 2**20:.1f} MB")
    print("  generate_rows(3) — generator, list() дає:", list(generate_rows(3)))
    print("  перші 5 рядків файлу (islice над read_lines):")
    for line in islice(read_lines(path), 5):
        print("   ", line.rstrip())
    print("  «брудний» рядок 13 та зіпсовані рядки 97, 194, 291, 388:")
    wanted = {13, 97, 194, 291, 388}
    with closing(read_lines(path)) as lines:              # closing() закриє генератор, а він — файл
        for number, line in enumerate(islice(lines, max(wanted) + 1)):
            if number in wanted:
                print(f"    {number:>3}: {line.rstrip()!r}")

    show("ITERABLE та ITERATOR: CsvDataset (контейнер) і LineReader (iterator)")
    dataset = CsvDataset(path)
    reader = iter(dataset)
    fresh: object = iter(dataset)
    print(f"  iter(dataset) is dataset -> {fresh is dataset}  (контейнер щоразу видає новий {type(fresh).__name__})")
    print(f"  iter(reader) is reader   -> {iter(reader) is reader}  (iterator повертає себе)")
    print("  next(reader) x3 ->", [next(reader).rstrip() for _ in range(3)])
    print(f"  reader.lines_read = {reader.lines_read}, файл відкрито: {not reader.closed}")
    rest = sum(1 for _ in reader)
    print(f"  цикл for дочитав решту: {fmt_int(rest)} рядків; після StopIteration файл закрито: {reader.closed}")
    try:
        next(reader)
    except StopIteration:
        print("  next(reader) ще раз -> StopIteration; list(reader) ->", list(reader), "(one-shot)")
    again = iter(dataset)
    print("  next(iter(dataset)) ->", repr(next(again).rstrip()), "(контейнер можна обійти знову)")
    again.close()

    show("GENERATOR FUNCTION і yield: read_lines()")
    lines = read_lines(path)
    print(f"  read_lines(path) -> {type(lines).__name__}, стан {getgeneratorstate(lines)}: файл ще не відкрито")
    print(f"  next(lines) -> {next(lines).rstrip()!r}, стан {getgeneratorstate(lines)}: функція «завмерла» на yield")
    lines.close()
    print(f"  lines.close() -> стан {getgeneratorstate(lines)}: блок with усередині генератора закрив файл")

    show("НЕСКІНЧЕННИЙ ГЕНЕРАТОР + islice")
    print("  list(islice(student_ids(200_001), 5)) ->", list(islice(student_ids(200_001), 5)))
    print("  list(student_ids()) не завершився б ніколи: count() не має кінця, а list() чекає на StopIteration")

    show("yield from: parse_rows() делегує csv.DictReader, flatten() — сам собі (рекурсія)")
    rows = parse_rows(clean_lines(read_lines(path)))
    print("  next(parse_rows(...)) ->", next(rows))
    rows.close()
    nested: list[Nested[int]] = [1, [2, 3], [4, [5, 6]]]
    print(f"  flatten({nested}) ->", list(flatten(nested)))

    show("GENERATOR EXPRESSION: сума всіх валідних балів без проміжного списку")
    grades = (record.grade for record in build_pipeline(path))
    print(f"  grades = (record.grade for record in build_pipeline(path)) -> {type(grades).__name__}")
    log.setLevel(logging.WARNING)
    print(f"  sum(grades) = {sum(grades):,.1f}".replace(",", " "))
    log.setLevel(logging.INFO)

    show(f"LAZY PIPELINE: перші 5 записів із балом >= {MINIMUM:g} (islice)")
    pipeline = build_pipeline(path, MINIMUM)
    for record in islice(pipeline, 5):
        print(" ", fmt(record))
    pipeline.close()
    print("  жодного рядка «[log] stage ... drained»: потік зупинено після п'яти записів, файл закрито")

    show("АГРЕГАЦІЯ ЗА ОДИН ПРОХІД: streaming_stats + ValidationReport (стадії логують, коли вичерпані)")
    report = ValidationReport()
    stats = streaming_stats(build_pipeline(path, MINIMUM, report))
    print(f"  рядків даних: {fmt_int(report.seen)}; валідних: {fmt_int(report.accepted)}; "
          f"відхилено: {fmt_int(sum(report.rejected.values()))}")
    for reason, number in sorted(report.rejected.items()):
        print(f"    {reason:<15} {number}")
    print(f"  із балом >= {MINIMUM:g}: {fmt_int(stats.count)} записів; середній {stats.average:.2f}; "
          f"min {stats.minimum}; max {stats.maximum}")
    print("  за групами:", dict(sorted(stats.per_group.items())))
    log.setLevel(logging.WARNING)
    print("  (далі логування стадій вимкнено)")

    show("ПІДРАХУНОК УСІХ ВАЛІДНИХ ЗАПИСІВ ЗА ГРУПАМИ (Counter поверх generator expression)")
    print(" ", dict(sorted(count_by_group(build_pipeline(path)).items())))

    show("TOP-5 НАЙКРАЩИХ (heapq.nlargest: у пам'яті лише п'ять записів)")
    for record in top_n(build_pipeline(path), 5):
        print(" ", fmt(record))

    show("БАТЧІ: batched(…, 50 000) та adaptive_batches(start=1 000, limit=64 000)")
    sizes = [len(batch) for batch in batched(build_pipeline(path), 50_000)]
    print(f"  batched:  {sizes}, разом {fmt_int(sum(sizes))}")
    sizes = [len(batch) for batch in adaptive_batches(build_pipeline(path), 1_000, 64_000)]
    print(f"  adaptive: {sizes}, разом {fmt_int(sum(sizes))}")

    show("groupby НА ОДНОМУ БАТЧІ (20 записів із балом >= 95, відсортованих за групою)")
    batches = batched(build_pipeline(path, 95.0), 20)
    batch = next(batches)
    batches.close()
    for group, members in by_group(batch):
        print(f"  {group:<8} {len(members):2}  ids {[m.student_id for m in members]}")

    show("accumulate / pairwise / takewhile / фільтр за групами")
    head = list(islice(build_pipeline(path), 6))
    print("  оцінки перших шести:   ", [record.grade for record in head])
    print("  running_average:       ", [round(value, 2) for value in running_average(r.grade for r in head)])
    print("  grade_changes:         ", [round(value, 1) for value in grade_changes(head)])
    early = list(with_min_grade(head_by_id(build_pipeline(path), 300), 90.0))
    print(f"  takewhile id <= 300, бал >= 90: {len(early)} записів, ids {[r.student_id for r in early]}")
    only_31 = list(islice(in_groups(build_pipeline(path, 95.0), ["ФЕП-31с"]), 3))
    print("  in_groups(ФЕП-31с), бал >= 95, перші 3:", [(r.student_id, r.grade) for r in only_31])

    show("chain: ОДИН ПОТІК ІЗ КІЛЬКОХ ФАЙЛІВ")
    parts = [ensure_dataset(DATA_DIR / f"students_{rows}.csv", rows) for rows in (10_000, 100_000)]
    print("  файли:", [part.name for part in parts])
    print(f"  записів у ланцюжку з балом >= {MINIMUM:g}: "
          f"{fmt_int(sum(1 for _ in build_multi_pipeline(parts, MINIMUM)))}")

    show("STREAMING EXPORT: студенти з балом >= 90 у новий файл")
    honours = DATA_DIR / "honours.csv"
    written = export_csv(build_pipeline(path, 90.0), honours)
    print(f"  {honours}: {fmt_int(written)} записів, {honours.stat().st_size / 2**10:.0f} KB")
    print("  перші 3 рядки:", [line.rstrip() for line in islice(read_lines(honours), 3)])

    show("МІСТ ДО ЛР2: to_grade_records + analytics.processors.count_records_by_group")
    first_thousand = islice(build_pipeline(path, MINIMUM), 1_000)
    bridged = list(to_grade_records(first_thousand, "Професійний Python"))
    print("  перший GradeRecord:", bridged[0])
    print("  count_records_by_group:", dict(sorted(count_records_by_group(bridged).items())))

    show("LAZY SEARCH ІЗ РАННІМ ЗАВЕРШЕННЯМ: find_first + LineReader.lines_read")
    reader = LineReader(path)
    hit = find_first(assemble(reader), is_excellent_in_33)
    print("  перший студент ФЕП-33 із балом >= 99:", fmt(hit))
    print(f"  прочитано рядків файлу: {fmt_int(reader.lines_read)} із {fmt_int(ROWS + 1)}")
    reader.close()

    show("ТИПОВІ ПОМИЛКИ")
    squares = (x * x for x in range(5))
    print("  вичерпаний генератор: list(g) ->", list(squares), " list(g) вдруге ->", list(squares))
    numbers = (int(value) for value in ["1", "2", "x"])
    print("  lazy exception: генератор створено без помилки; споживання ->", end=" ")
    try:
        print([next(numbers) for _ in range(3)])
    except ValueError as error:
        print(f"ValueError: {error}")
    missing = build_pipeline(DATA_DIR / "missing.csv")
    print("  build_pipeline('missing.csv') створено без помилки; next() ->", end=" ")
    try:
        next(missing)
    except FileNotFoundError:
        print("FileNotFoundError лише під час споживання")

    show("ЕКСПЕРИМЕНТ: eager (list на кожній стадії) проти lazy (generator), поріг 85")
    print("  time — без tracemalloc; peak — з tracemalloc; «1st» — час до першого результату")
    results = experiment.run(DATA_DIR)
    print(experiment.format_table(results))

    show(f"РАННЄ ЗАВЕРШЕННЯ НА {fmt_int(experiment.EARLY_SIZE)} ЗАПИСАХ")
    big = ensure_dataset(DATA_DIR / f"students_{experiment.EARLY_SIZE}.csv", experiment.EARLY_SIZE)
    early_result = experiment.early_termination(big, experiment.EARLY_SIZE, is_excellent_in_33)
    print(f"  lazy find_first: {fmt_seconds(early_result.lazy_time):>9}, "
          f"прочитано {fmt_int(early_result.lines_pulled)} рядків -> {fmt(early_result.lazy_hit)}")
    print(f"  eager список:    {fmt_seconds(early_result.eager_time):>9}, "
          f"прочитано {fmt_int(experiment.EARLY_SIZE + 1)} рядків -> {fmt(early_result.eager_hit)}")


if __name__ == "__main__":
    main()
