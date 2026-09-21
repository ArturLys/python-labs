from student_manager.registry import Calculator


def render_history(calc: Calculator) -> str:
    return "
".join(f"{op.left} {op.symbol} {op.right} = {op.result}" for op in calc.history)
