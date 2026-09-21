from student_manager.models import Operation


class Calculator:
    def __init__(self) -> None:
        self.history: list[Operation] = []

    def apply(self, symbol: str, left: float, right: float) -> float:
        if symbol == "+":
            result = left + right
        elif symbol == "-":
            result = left - right
        elif symbol == "*":
            result = left * right
        elif symbol == "/":
            if right == 0:
                raise ZeroDivisionError("division by zero")
            result = left / right
        else:
            raise ValueError(f"unknown operation {symbol!r}")
        self.history.append(Operation(symbol, left, right, result))
        return result
