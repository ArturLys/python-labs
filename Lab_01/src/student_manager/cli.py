"""Console interface: text tables and the interactive menu. No business logic here."""

from __future__ import annotations

from collections.abc import Callable

from student_manager.exceptions import PersonManagerError
from student_manager.models import Person
from student_manager.registry import PersonRegistry

HEADER = f"{'Студент':<26}{'Група':<10}{'Середній бал':>13}"
RULE = "-" * len(HEADER)
MENU = """
1. Усі студенти
2. Додати студента
3. Студенти групи
4. Найкращий студент
5. Середній бал групи
6. Рейтинг
7. Пошук
0. Вихід"""


def format_persons(persons: list[Person], title: str) -> str:
    if not persons:
        return f"{title}\n{RULE}\n(порожньо)"
    rows = [f"{s.full_name:<26}{s.group:<10}{s.average_grade:>13.2f}" for s in persons]
    return "\n".join([title, HEADER, RULE, *rows])


def parse_grade(text: str) -> float:
    """'87,5' and '87.5' are both fine; anything else is a ValueError with a readable message."""
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"'{text}' не є числом") from None


def read_person(ask: Callable[[str], str] = input) -> Person:
    first_name = ask("Ім'я: ")
    last_name = ask("Прізвище: ")
    group = ask("Група: ")
    grade = parse_grade(ask("Середній бал: "))
    return Person(first_name, last_name, group, grade)


def run_menu(registry: PersonRegistry, ask: Callable[[str], str] = input) -> None:
    """Menu loop. `ask` is injectable so the loop can be tested without a keyboard."""

    def show_all() -> None:
        print(format_persons(registry.all(), "УСІ СТУДЕНТИ"))

    def add() -> None:
        person = registry.add(read_person(ask))
        print(f"Додано: {person.full_name}, {person.group}, {person.average_grade:.2f}")

    def show_group() -> None:
        group = ask("Група: ")
        print(format_persons(registry.by_group(group), f"ГРУПА {group.strip()}"))

    def show_best() -> None:
        best = registry.best()
        print(f"Найкращий студент: {best.full_name} ({best.group}, {best.average_grade:.2f})")

    def show_average() -> None:
        group = ask("Група: ")
        print(f"Середній бал групи {group.strip()}: {registry.group_average(group):.2f}")

    def show_rating() -> None:
        print(format_persons(registry.sorted_by_grade(), "РЕЙТИНГ"))

    def search() -> None:
        last_name = ask("Прізвище (Enter — будь-яке): ").strip() or None
        group = ask("Група (Enter — будь-яка): ").strip() or None
        raw = ask("Мінімальний бал (Enter — без обмеження): ").strip()
        min_grade = parse_grade(raw) if raw else None
        print(format_persons(registry.search(last_name=last_name, group=group, min_grade=min_grade), "ПОШУК"))

    actions: dict[str, Callable[[], None]] = {
        "1": show_all, "2": add, "3": show_group, "4": show_best,
        "5": show_average, "6": show_rating, "7": search,
    }
    while True:
        print(MENU)
        choice = ask("Команда: ").strip()
        if choice == "0":
            print("До побачення.")
            return
        action = actions.get(choice)
        if action is None:
            print("Невідома команда.")
            continue
        try:
            action()
        except PersonManagerError as error:
            print(f"Помилка: {error}")
        except ValueError as error:
            print(f"Некоректні дані: {error}")
