from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from .numeric_index import NumericIndex
from .evaluator import evaluate
from .index import HashIndex
from .query import And, Comparison, Not, Or
from .storage import RecordStore
from .numeric_index import NumericIndex
from .index import HashIndex


@dataclass

class QueryPlan:
    strategy: str
    index_field: str | None = None
    operator: str | None = None
    value: Any = None
    reason: str | None = None
class QueryPlanner:
    """Chooses an execution strategy for a query."""

    def __init__(
            self,
            indexed_fields: set[str],
            numeric_indexed_fields: set[str] | None = None,
    ):
        self.indexed_fields = indexed_fields
        self.numeric_indexed_fields = (
                numeric_indexed_fields or set()
        )

    def plan(self, expression: Any) -> QueryPlan:

        comparison = self._find_indexable_comparison(
            expression
        )

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

        numeric = self._find_numeric_comparison(
            expression
        )

        if numeric is not None:
            return QueryPlan(
                strategy="NUMERIC_INDEX_SCAN",
                index_field=numeric.field,
                operator=numeric.operator,
                value=numeric.value,
                reason=(
                    f"Range lookup on numeric indexed "
                    f"field '{numeric.field}'"
                ),
            )

        return QueryPlan(
            strategy="FULL_SCAN",
            reason=(
                "No suitable index was found"
            ),
        )

    def _find_numeric_comparison(
            self,
            expression: Any,
    ) -> Comparison | None:

        if isinstance(expression, Comparison):

            if (
                    expression.field
                    in self.numeric_indexed_fields
                    and expression.operator
                    in {">", ">=", "<", "<="}
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                    self._find_numeric_comparison(
                        expression.left
                    )
                    or self._find_numeric_comparison(
                expression.right
            )
            )

        if isinstance(expression, Or):
            return (
                    self._find_numeric_comparison(
                        expression.left
                    )
                    or self._find_numeric_comparison(
                expression.right
            )
            )

        return None
    def _find_indexable_comparison(
            self,
            expression: Any,
    ) -> Comparison | None:

        if isinstance(expression, Comparison):

            if (
                    expression.operator == "="
                    and expression.field in self.indexed_fields
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                    self._find_indexable_comparison(
                        expression.left
                    )
                    or self._find_indexable_comparison(
                expression.right
            )
            )

        if isinstance(expression, Or):
            return (
                    self._find_indexable_comparison(
                        expression.left
                    )
                    or self._find_indexable_comparison(
                expression.right
            )
            )

        if isinstance(expression, Not):
            return None

        return None


class QueryExecutor:
    """Executes query expressions against a RecordStore."""

    def __init__(
            self,
            store: RecordStore,
            indexes: dict[str, HashIndex],
            numeric_indexes: dict[str, NumericIndex] | None = None,
    ):
        self.store = store
        self.indexes = indexes
        self.numeric_indexes = (
                numeric_indexes or {}
        )

    def execute(
            self,
            expression: Any,
    ) -> Iterable[tuple[int, dict[str, Any]]]:

        planner = QueryPlanner(
            set(self.indexes.keys()),
            set(self.numeric_indexes.keys()),
        )

        plan = planner.plan(expression)

        if plan.strategy == "INDEX_SCAN":

            yield from self._index_scan(
                expression,
                plan.index_field,
            )

        elif plan.strategy == "NUMERIC_INDEX_SCAN":

            yield from self._numeric_index_scan(
                expression,
                plan.index_field,
            )

        else:

            yield from self._full_scan(
                expression
            )

    def _numeric_index_scan(
            self,
            expression: Any,
            index_field: str | None,
    ) -> Iterable[tuple[int, dict[str, Any]]]:

        if index_field is None:
            yield from self._full_scan(expression)
            return

        comparison = self._find_comparison(
            expression,
            index_field,
        )

        if comparison is None:
            yield from self._full_scan(expression)
            return

        index = self.numeric_indexes.get(
            index_field
        )

        if index is None:
            yield from self._full_scan(expression)
            return

        if comparison.operator == ">":
            candidate_ids = index.greater_than(
                comparison.value
            )

        elif comparison.operator == ">=":
            candidate_ids = index.greater_equal(
                comparison.value
            )

        elif comparison.operator == "<":
            candidate_ids = index.less_than(
                comparison.value
            )

        elif comparison.operator == "<=":
            candidate_ids = index.less_equal(
                comparison.value
            )

        else:
            yield from self._full_scan(expression)
            return

        for record_id in sorted(candidate_ids):

            record = self.store.get(
                record_id
            )

            if evaluate(
                    expression,
                    record,
            ):
                yield record_id, record
    def _index_scan(
        self,
        expression: Any,
        index_field: str | None,
    ) -> Iterable[tuple[int, dict[str, Any]]]:

        if index_field is None:
            yield from self._full_scan(expression)
            return

        comparison = self._find_comparison(
            expression,
            index_field,
        )

        if comparison is None:
            yield from self._full_scan(expression)
            return

        index = self.indexes[index_field]

        candidate_ids = index.lookup(
            comparison.value
        )

        for record_id in sorted(candidate_ids):
            record = self.store.get(record_id)

            if evaluate(expression, record):
                yield record_id, record

    def _full_scan(
        self,
        expression: Any,
    ) -> Iterable[tuple[int, dict[str, Any]]]:

        for record_id, record in self.store.scan():

            if evaluate(expression, record):
                yield record_id, record

    def _find_comparison(
        self,
        expression: Any,
        field: str,
    ) -> Comparison | None:

        if isinstance(expression, Comparison):

            if (
                expression.field == field
                and expression.operator == "="
            ):
                return expression

            return None

        if isinstance(expression, And):
            return (
                self._find_comparison(
                    expression.left,
                    field,
                )
                or self._find_comparison(
                    expression.right,
                    field,
                )
            )

        if isinstance(expression, Or):
            return (
                self._find_comparison(
                    expression.left,
                    field,
                )
                or self._find_comparison(
                    expression.right,
                    field,
                )
            )

        return None