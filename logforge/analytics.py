from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def count(
    records: Iterable[dict[str, Any]],
) -> int:
    return sum(1 for _ in records)


def numeric_stats(
    records: Iterable[dict[str, Any]],
    field: str,
) -> dict[str, Any]:

    values: list[int | float] = []

    for record in records:
        value = record.get(field)

        if isinstance(value, bool):
            continue

        if isinstance(value, (int, float)):
            values.append(value)

    if not values:
        return {
            "field": field,
            "count": 0,
            "min": None,
            "max": None,
            "sum": 0,
            "avg": None,
        }

    total = sum(values)

    return {
        "field": field,
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "sum": total,
        "avg": total / len(values),
    }


def group_by(
    records: Iterable[dict[str, Any]],
    field: str,
) -> dict[Any, int]:

    groups: dict[Any, int] = defaultdict(int)

    for record in records:
        value = record.get(field)

        groups[value] += 1

    return dict(groups)


def group_by_numeric(
    records: Iterable[dict[str, Any]],
    group_field: str,
    aggregate_field: str,
) -> dict[Any, dict[str, Any]]:

    values: dict[Any, list[float | int]] = defaultdict(list)

    for record in records:

        group = record.get(group_field)
        value = record.get(aggregate_field)

        if isinstance(value, bool):
            continue

        if isinstance(value, (int, float)):
            values[group].append(value)

    result = {}

    for group, group_values in values.items():

        total = sum(group_values)

        result[group] = {
            "count": len(group_values),
            "min": min(group_values),
            "max": max(group_values),
            "sum": total,
            "avg": total / len(group_values),
        }

    return result