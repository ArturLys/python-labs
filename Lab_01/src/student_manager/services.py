"""Function-style business logic over a plain list of persons (the same operations the registry offers)."""

from student_manager.models import Person


def calculate_group_average(persons: list[Person]) -> float:
    if not persons:
        return 0.0
    return sum(person.average_grade for person in persons) / len(persons)


def find_best_person(persons: list[Person]) -> Person | None:
    if not persons:
        return None
    return max(persons, key=lambda person: person.average_grade)


def filter_by_group(persons: list[Person], group: str) -> list[Person]:
    return [person for person in persons if person.group.casefold() == group.casefold()]


def find_person(persons: list[Person], last_name: str) -> Person | None:
    for person in persons:
        if person.last_name.casefold() == last_name.casefold():
            return person
    return None
