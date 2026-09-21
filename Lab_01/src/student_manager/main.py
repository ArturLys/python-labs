"""Application entry point: a scripted demo by default, the interactive menu with --menu."""

from __future__ import annotations

import argparse
import io
import sys

from student_manager import __version__
from student_manager.cli import format_persons, run_menu
from student_manager.exceptions import PersonManagerError
from student_manager.models import Person
from student_manager.registry import PersonRegistry


def demo_registry() -> PersonRegistry:
    return PersonRegistry([
        Person("Марта", "Гнатишин", "ФЕП-31с", 93.4),
        Person("Остап", "Дзюба", "ФЕП-31с", 78.9),
        Person("Соломія", "Кравець", "ФЕП-32", 88.1),
        Person("Тарас", "Вовк", "ФЕП-31с", 85.0),
        Person("Ірина", "Пасічник", "ФЕП-32", 96.7),
        Person("Юрій", "Скиба", "ФЕП-33", 71.2),
    ])


def run_demo(registry: PersonRegistry) -> None:
    group = "ФЕП-31с"
    print(format_persons(registry.all(), "УСІ СТУДЕНТИ"))
    print()
    print(format_persons(registry.by_group(group), f"ГРУПА {group}"))
    print(f"\nСередній бал групи {group}: {registry.group_average(group):.2f}")

    best = registry.best()
    print(f"Найкращий студент: {best.full_name} ({best.group}, {best.average_grade:.2f})")
    best_in_group = registry.best(group)
    print(f"Найкращий у {group}: {best_in_group.full_name} ({best_in_group.average_grade:.2f})")

    print()
    print(format_persons(registry.sorted_by_grade(), "РЕЙТИНГ"))
    print()
    print(format_persons(registry.search(group="ФЕП-32", min_grade=90), "ПОШУК: група ФЕП-32, бал >= 90"))

    stats = registry.statistics()
    print(f"\nСтатистика: {stats['count']} студентів, середній бал {stats['mean']:.2f}, "
          f"min {stats['min']:.1f}, max {stats['max']:.1f}, відмінників {stats['excellent']}")

    print("\nСпроба додати студента з балом 120:")
    try:
        registry.add(Person("Хтось", "Новий", "ФЕП-31с", 120.0))
    except PersonManagerError as error:
        print(f"  відхилено — {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="person-manager", description="Облік студентів")
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
