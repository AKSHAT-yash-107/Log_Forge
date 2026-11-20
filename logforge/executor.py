from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .evaluator import evaluate
from .index import HashIndex
from .numeric_index import NumericIndex
from .query import And, Comparison
from .storage import RecordStore


@dataclass
class QueryPlan:
    """Describes the execution strategy selected for a query."""

    strategy: str
    index_field: str | None = None
    operator: str | None = None
    value: Any = None
    reason: str | None = None


class QueryPlanner:
    """Chooses a safe execution strategy for a query expression."""

    def __init__(
        self,
        indexed_fields: set[str],
        numeric_indexed_fields: set[str] | None = None,
    ) -> None:
        self.indexed_fields = indexed_fields
        self.numeric_indexed_fields = (
            numeric_indexed_fields
            if numeric_indexed_fields is not None
            else set()
        )

    def plan(self, expression: Any) -> QueryPlan:
        """Choose an index scan only when its candidate set is safe."""

        comparison = self._find_indexable_comparison(expression)

        if comparison is not None:
            return QueryPlan(
                strategy="INDEX_SCAN",
                index_field=comparison.field,
                operator=comparison.operator,
                value=comparison.value,
                reason=(
                    f"Equality lookup on indexed field "
                    f"'{comparison.field}'"
                ),
            )

        numeric = self._find_numeric_comparison(expression)

        if numeric is not None:
            return QueryPlan(
                strategy="NUMERIC_INDEX_SCAN",
                index_field=numeric.field,
                operator=numeric.operator,
                value=numeric.value,
                reason=(
                    f"Range lookup on numeric indexed field "
                    f"'{numeric.field}'"
                ),
            )

        return QueryPlan(
            strategy="FULL_SCAN",
            reason="No suitable safe index condition was found",
        )

    def _find_numeric_comparison(
        self,
        expression: Any,
    ) -> Comparison | None:
        """Find a safe numeric range condition in an AND expression."""

        if isinstance(expression, Comparison):
            if (
                expression.field in self.numeric_indexed_fields
                and expression.operator in {">", ">=", "<", "<="}
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                self._find_numeric_comparison(expression.left)
                or self._find_numeric_comparison(expression.right)
            )

        # Never select one branch of OR or a condition inside NOT.
        return None

    def _find_indexable_comparison(
        self,
        expression: Any,
    ) -> Comparison | None:
        """Find a safe equality condition in an AND expression."""

        if isinstance(expression, Comparison):
            if (
                expression.operator == "="
                and expression.field in self.indexed_fields
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                self._find_indexable_comparison(expression.left)
                or self._find_indexable_comparison(expression.right)
            )

        # Never select one branch of OR or a condition inside NOT.
        return None


class QueryExecutor:
    """Executes query expressions against a RecordStore."""

    def __init__(
        self,
        store: RecordStore,
        indexes: dict[str, HashIndex],
        numeric_indexes: dict[str, NumericIndex] | None = None,
    ) -> None:
        self.store = store
        self.indexes = indexes
        self.numeric_indexes = (
            numeric_indexes
            if numeric_indexes is not None
            else {}
        )

    def execute(
        self,
        expression: Any,
        select_fields: list[str] | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        """Execute a query with optional projection, sorting, and limit."""

        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        if limit == 0:
            return

        planner = QueryPlanner(
            indexed_fields=set(self.indexes),
            numeric_indexed_fields=set(self.numeric_indexes),
        )
        plan = planner.plan(expression)

        if plan.strategy == "INDEX_SCAN":
            results = self._index_scan(
                expression,
                plan.index_field,
            )
        elif plan.strategy == "NUMERIC_INDEX_SCAN":
            results = self._numeric_index_scan(
                expression,
                plan.index_field,
            )
        else:
            results = self._full_scan(expression)

        # Sorting requires all matching records to be available.
        records = list(results)

        if order_by is not None:
            for _, record in records:
                if order_by not in record:
                    raise ValueError(
                        f"Cannot sort by unknown field: {order_by}"
                    )

            # Separate NULL and non-NULL records.
            non_null_records = [
                item for item in records
                if item[1].get(order_by) is not None
            ]

            null_records = [
                item for item in records
                if item[1].get(order_by) is None
            ]

            # Apply sorting direction only to actual values.
            non_null_records.sort(
                key=lambda item: self._sort_key(item[1].get(order_by)),
                reverse=descending,
            )

            # NULL values always remain at the end.
            records = non_null_records + null_records

        if limit is not None:
            records = records[:limit]

        for record_id, record in records:
            if select_fields is not None:
                projected = {
                    field: record.get(field)
                    for field in select_fields
                }
                yield record_id, projected
            else:
                yield record_id, record

    def _numeric_index_scan(
        self,
        expression: Any,
        index_field: str | None,
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        """Use a numeric range index, then evaluate the complete predicate."""

        if index_field is None:
            yield from self._full_scan(expression)
            return

        comparison = self._find_comparison(
            expression,
            index_field,
            {">", ">=", "<", "<="},
        )
        if comparison is None:
            yield from self._full_scan(expression)
            return

        index = self.numeric_indexes.get(index_field)
        if index is None:
            yield from self._full_scan(expression)
            return

        if comparison.operator == ">":
            candidate_ids = index.greater_than(comparison.value)
        elif comparison.operator == ">=":
            candidate_ids = index.greater_equal(comparison.value)
        elif comparison.operator == "<":
            candidate_ids = index.less_than(comparison.value)
        elif comparison.operator == "<=":
            candidate_ids = index.less_equal(comparison.value)
        else:
            # Defensive fallback if the index contract changes.
            yield from self._full_scan(expression)
            return

        for record_id in sorted(candidate_ids):
            record = self.store.get(record_id)

            # The index checks only one condition. The full AST is authoritative.
            if evaluate(expression, record):
                yield record_id, record

    @staticmethod
    def _sort_key(value: Any) -> tuple[int, int, Any]:
        """Return a comparable key, placing None values last."""

        if value is None:
            return (1, 0, "")

        if isinstance(value, bool):
            return (0, 0, int(value))

        if isinstance(value, (int, float)):
            return (0, 0, value)

        # Keep strings and other values in a separate comparison group so
        # mixed numeric/string columns do not raise TypeError during sorting.
        return (0, 1, str(value))

    def _index_scan(
        self,
        expression: Any,
        index_field: str | None,
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        """Use an equality index, then evaluate the complete predicate."""

        if index_field is None:
            yield from self._full_scan(expression)
            return

        comparison = self._find_comparison(
            expression,
            index_field,
            {"="},
        )
        if comparison is None:
            yield from self._full_scan(expression)
            return

        index = self.indexes.get(index_field)
        if index is None:
            yield from self._full_scan(expression)
            return

        candidate_ids = index.lookup(comparison.value)

        for record_id in sorted(candidate_ids):
            record = self.store.get(record_id)

            # Recheck every condition, including non-indexed AND conditions.
            if evaluate(expression, record):
                yield record_id, record

    def _full_scan(
        self,
        expression: Any,
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        """Evaluate the complete expression against every stored record."""

        for record_id, record in self.store.scan():
            if evaluate(expression, record):
                yield record_id, record

    def _find_comparison(
        self,
        expression: Any,
        field: str,
        operators: set[str],
    ) -> Comparison | None:
        """
        Find a comparison usable by the selected index.

        Only AND branches are traversed. A comparison inside OR cannot
        independently produce a complete candidate set for the whole query.
        NOT is also deliberately not traversed.
        """

        if isinstance(expression, Comparison):
            if (
                expression.field == field
                and expression.operator in operators
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                self._find_comparison(
                    expression.left,
                    field,
                    operators,
                )
                or self._find_comparison(
                    expression.right,
                    field,
                    operators,
                )
            )

        # Do not descend into Or or Not nodes.
        return None
