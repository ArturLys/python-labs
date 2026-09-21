from .cli import render_history
from .registry import Calculator


def main() -> None:
    calc = Calculator()
    calc.apply("+", 2, 3)
    print(render_history(calc))


if __name__ == "__main__":
    main()
