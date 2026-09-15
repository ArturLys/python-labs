"""Demo of the analytics module: `python -m student_manager.analytics`."""

from __future__ import annotations

import io
import sys

from student_manager.analytics import benchmark
from student_manager.analytics.analytics import (
    above_threshold,
    best_student,
    discipline_averages,
    group_averages,
    make_record,
    make_threshold_filter,
    mean_of,
    pipeline,
    ranking,
    student_averages,
    summary,
)
from student_manager.analytics.data import GradeRecord, load_records
from student_manager.analytics.decorators import RECENT_CALLS
from student_manager.analytics.processors import (
    count_records_by_group,
    filter_items,
    find_linear,
    group_by,
    index_by_student,
    nested_grouping,
    sort_items,
    students_per_group,
    unique_disciplines,
    unique_groups,
)


def show(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def print_records(records: list[GradeRecord]) -> None:
    for r in records:
        print(f"  {r.student:<18} {r.group:<9} {r.discipline:<20} {r.grade:5.1f}")


def print_scores(scores: list[tuple[str, float]]) -> None:
    for place, (student, average) in enumerate(scores, 1):
        print(f"  {place:2}. {student:<18} {average:6.2f}")


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    records = load_records()

    show(f"УСІ ЗАПИСИ ({len(records)}), перші 8")
    print_records(records[:8])

    show("УНІКАЛЬНІ ГРУПИ ТА ДИСЦИПЛІНИ (set)")
    print("  групи:      ", sorted(unique_groups(records)))
    print("  дисципліни: ", sorted(unique_disciplines(records)))

    show("СЕРЕДНІЙ БАЛ КОЖНОГО СТУДЕНТА (dict, @measure_time)")
    for student, average in student_averages(records).items():
        print(f"  {student:<18} {average:6.2f}")

    show("НАЙКРАЩИЙ СТУДЕНТ (max + lambda, @log_calls)")
    student, average = best_student(records)
    print(f"  {student} — {average:.2f}")

    show("РЕЙТИНГ (sorted + lambda)")
    print_scores(ranking(records))

    show("СТУДЕНТИ З БАЛОМ >= 85 (closure make_threshold_filter)")
    print_scores(above_threshold(records, 85))

    show("СЕРЕДНІЙ БАЛ ГРУП І ДИСЦИПЛІН")
    for group, avg in sorted(group_averages(records).items()):
        print(f"  {group:<9} {avg:6.2f}")
    for discipline, avg in discipline_averages(records).items():
        print(f"  {discipline:<20} {avg:6.2f}")

    show("КІЛЬКІСТЬ ЗАПИСІВ І СТУДЕНТІВ У ГРУПАХ (Counter, dict comprehension)")
    counter = count_records_by_group(records)
    per_group = students_per_group(records)
    for group, count in sorted(counter.items()):
        print(f"  {group:<9} записів {count:2}  студентів {per_group[group]}")
    print("  найбільша група:", counter.most_common(1)[0])

    show("ГРУПУВАННЯ (defaultdict) ТА ВКЛАДЕНЕ ГРУПУВАННЯ")
    for group, members in sorted(group_by(records, lambda r: r.group).items()):
        print(f"  {group}: {len(members)} записів")
    nested = nested_grouping(records)
    print("  ФЕП-32 / Мова С:", [(r.student, r.grade) for r in nested["ФЕП-32"]["Мова С"]])

    show("ПОШУК: index (dict) проти лінійного (list)")
    index = index_by_student(records)
    print("  index['Тимків Богдан']:", [r.grade for r in index["Тимків Богдан"]])
    print("  find_linear(...):      ", [r.grade for r in find_linear(records, "Тимків Богдан")])

    show("УНІВЕРСАЛЬНІ filter_items / sort_items (lambda)")
    strong_python = filter_items(records, lambda r: r.discipline == "Професійний Python" and r.grade >= 90)
    print_records(sort_items(strong_python, key=lambda r: r.grade, reverse=True))

    show("*args, **kwargs")
    print("  mean_of(90, 85, 77):", mean_of(90, 85, 77))
    print(
        "  make_record(**fields):",
        make_record(student="Новий Студент", group="ФЕП-31с", discipline="Мова С", grade=88.0),
    )

    show("PIPELINE: рейтинг -> поріг 80 -> перші три")
    top = pipeline(
        ranking(records),
        lambda scores: [s for s in scores if make_threshold_filter(80)(s)],
        lambda scores: scores[:3],
    )
    print_scores(top)

    show("ПІДСУМОК (aggregation)")
    for key, value in summary(records).items():
        print(f"  {key:<10} {value}")

    show("ОСТАННІ ОПЕРАЦІЇ (deque maxlen=5)")
    print(" ", list(RECENT_CALLS))

    show("BENCHMARK: лінійний пошук у list проти dict-index")
    print(benchmark.format_table(benchmark.run()))


if __name__ == "__main__":
    main()
