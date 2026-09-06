from __future__ import annotations

from typing import Any

from .query import And, Comparison, Not, Or


def compare(
    actual: Any,
    operator: str,
    expected: Any,
) -> bool:
    if actual is None:
        if operator == "=":
            return expected is None

        if operator == "!=":
            return expected is not None

        return False

    try:
        if operator == "=":
            return actual == expected

        if operator == "!=":
            return actual != expected

        if operator == ">":
            return actual > expected

        if operator == ">=":
            return actual >= expected

        if operator == "<":
            return actual < expected

        if operator == "<=":
            return actual <= expected

    except TypeError:
        return False

    raise ValueError(
        f"Unsupported operator: {operator}"
    )


def evaluate(
    expression: Any,
    record: dict[str, Any],
) -> bool:

    if isinstance(expression, Comparison):

        actual = record.get(
            expression.field
        )

        return compare(
            actual,
            expression.operator,
            expression.value,
        )

    if isinstance(expression, And):

        return (
            evaluate(expression.left, record)
            and evaluate(expression.right, record)
        )

    if isinstance(expression, Or):

        return (
            evaluate(expression.left, record)
            or evaluate(expression.right, record)
        )

    if isinstance(expression, Not):

        return not evaluate(
            expression.expression,
            record,
        )

    raise ValueError(
        f"Unknown expression type: "
        f"{type(expression).__name__}"
    )