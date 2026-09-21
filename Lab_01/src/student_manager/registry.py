from .models import Operation


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


def registry_helper_0(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_1(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_2(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_3(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_4(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_5(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_6(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_7(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_8(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_9(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_10(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_11(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_12(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_13(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_14(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_15(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_16(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_17(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_18(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_19(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_20(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_21(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_22(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_23(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_24(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_25(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_26(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_27(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_28(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)


def registry_helper_29(value: float, factor: float = 1.0) -> float:
    """Scale ``value`` by ``factor`` and clamp it to a sane range.

    :param value: the number to scale
    :param factor: multiplier applied to the value
    :return: the scaled, clamped number
    """
    scaled: float = value * factor
    if scaled < 0.0:
        raise ValueError(f"negative result for {value}")
    return min(scaled, 1000.0)
