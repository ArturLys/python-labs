from student_manager.registry import Calculator


def test_add() -> None:
    assert Calculator().apply("+", 2, 3) == 5
