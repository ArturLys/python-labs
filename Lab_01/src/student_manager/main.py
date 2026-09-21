"""Application entry point: a scripted demo by default, the interactive menu with --menu."""

from __future__ import annotations

import argparse
import io
import sys

from student_manager import __version__
from student_manager.cli import format_students, run_menu
from student_manager.exceptions import StudentManagerError
from student_manager.models import Student
from student_manager.registry import StudentRegistry


def demo_registry() -> StudentRegistry:
    return StudentRegistry([
        Student("Марта", "Гнатишин", "ФЕП-31с", 93.4),
        Student("Остап", "Дзюба", "ФЕП-31с", 78.9),
        Student("Соломія", "Кравець", "ФЕП-32", 88.1),
        Student("Тарас", "Вовк", "ФЕП-31с", 85.0),
        Student("Ірина", "Пасічник", "ФЕП-32", 96.7),
        Student("Юрій", "Скиба", "ФЕП-33", 71.2),
    ])


def run_demo(registry: StudentRegistry) -> None:
    group = "ФЕП-31с"
    print(format_students(registry.all(), "УСІ СТУДЕНТИ"))
    print()
    print(format_students(registry.by_group(group), f"ГРУПА {group}"))
    print(f"\nСередній бал групи {group}: {registry.group_average(group):.2f}")

    best = registry.best()
    print(f"Найкращий студент: {best.full_name} ({best.group}, {best.average_grade:.2f})")
    best_in_group = registry.best(group)
    print(f"Найкращий у {group}: {best_in_group.full_name} ({best_in_group.average_grade:.2f})")

    print()
    print(format_students(registry.sorted_by_grade(), "РЕЙТИНГ"))
    print()
    print(format_students(registry.search(group="ФЕП-32", min_grade=90), "ПОШУК: група ФЕП-32, бал >= 90"))

    stats = registry.statistics()
    print(f"\nСтатистика: {stats['count']} студентів, середній бал {stats['mean']:.2f}, "
          f"min {stats['min']:.1f}, max {stats['max']:.1f}, відмінників {stats['excellent']}")

    print("\nСпроба додати студента з балом 120:")
    try:
        registry.add(Student("Хтось", "Новий", "ФЕП-31с", 120.0))
    except StudentManagerError as error:
        print(f"  відхилено — {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="student-manager", description="Облік студентів")
    parser.add_argument("--menu", action="store_true", help="інтерактивне меню замість демонстрації")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    registry = demo_registry()
    if args.menu:
        run_menu(registry)
    else:
        run_demo(registry)


if __name__ == "__main__":
    main()
