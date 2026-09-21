from .cli import render_history
from .logic import Calculator


def main() -> None:
    calc = Calculator()
    calc.apply("+", 2, 3)
    calc.apply("*", 4, 2.5)
    print(render_history(calc))


if __name__ == "__main__":
    main()
