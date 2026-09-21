from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    symbol: str
    left: float
    right: float
    result: float
