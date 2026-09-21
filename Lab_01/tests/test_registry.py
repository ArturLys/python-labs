import pytest

from records_app.exceptions import InvalidGradeError, InvalidGroupError, StudentNotFoundError
from records_app.models import Student
from records_app.registry import StudentRegistry


@pytest.fixture
def registry() -> StudentRegistry:
    return StudentRegistry([
        Student("Марта", "Гнатишин", "ФЕП-31с", 93.4),
        Student("Остап", "Дзюба", "ФЕП-31с", 78.9),
        Student("Соломія", "Кравець", "ФЕП-32", 88.1),
    ])


def test_by_group_ignores_case_and_spaces(registry: StudentRegistry) -> None:
    assert [s.last_name for s in registry.by_group(" феп-31с ")] == ["Гнатишин", "Дзюба"]


def test_group_average(registry: StudentRegistry) -> None:
    assert registry.group_average("ФЕП-31с") == pytest.approx(86.15)


def test_best_overall_and_inside_group(registry: StudentRegistry) -> None:
    assert registry.best().last_name == "Гнатишин"
    assert registry.best("ФЕП-32").last_name == "Кравець"


def test_best_of_unknown_group_raises(registry: StudentRegistry) -> None:
    with pytest.raises(StudentNotFoundError):
        registry.best("ФЕП-99")


def test_grade_outside_scale_is_rejected() -> None:
    with pytest.raises(InvalidGradeError):
        Student("Ім'я", "Прізвище", "ФЕП-31с", 101.0)


def test_group_name_is_validated() -> None:
    with pytest.raises(InvalidGroupError):
        Student("Ім'я", "Прізвище", "група 31", 50.0)


def test_duplicate_student_is_rejected(registry: StudentRegistry) -> None:
    with pytest.raises(ValueError):
        registry.add(Student("Марта", "Гнатишин", "ФЕП-31с", 50.0))


def test_search_combines_criteria(registry: StudentRegistry) -> None:
    found = registry.search(group="ФЕП-31с", min_grade=80)
    assert [s.last_name for s in found] == ["Гнатишин"]


def test_rating_is_descending(registry: StudentRegistry) -> None:
    grades = [s.average_grade for s in registry.sorted_by_grade()]
    assert grades == sorted(grades, reverse=True)
