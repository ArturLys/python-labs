"""Function-style business logic over a plain list of students (the same operations the registry offers)."""

from student_manager.models import Student


def calculate_group_average(students: list[Student]) -> float:
    if not students:
        return 0.0
    return sum(student.average_grade for student in students) / len(students)


def find_best_student(students: list[Student]) -> Student | None:
    if not students:
        return None
    return max(students, key=lambda student: student.average_grade)


def filter_by_group(students: list[Student], group: str) -> list[Student]:
    return [student for student in students if student.group.casefold() == group.casefold()]


def find_student(students: list[Student], last_name: str) -> Student | None:
    for student in students:
        if student.last_name.casefold() == last_name.casefold():
            return student
    return None
