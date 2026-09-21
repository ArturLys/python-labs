import pytest

from calc_app.logic import Calculator


def test_add() -> None:
    assert Calculator().apply("+", 2, 3) == 5


def test_div_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        Calculator().apply("/", 1, 0)
