
import tempfile
import unittest

from logforge.numeric_index import NumericIndex
from logforge.executor import (
    QueryExecutor,
    QueryPlanner,
)
from logforge.index import HashIndex
from logforge.query import parse_query
from logforge.storage import RecordStore


class TestQueryPlanner(unittest.TestCase):

    def test_index_plan(self):
        planner = QueryPlanner({"status"})

        expression = parse_query("status = 500")

        plan = planner.plan(expression)

        self.assertEqual(
            plan.strategy,
            "INDEX_SCAN",
        )

        self.assertEqual(
            plan.index_field,
            "status",
        )

    def test_full_scan_plan(self):
        planner = QueryPlanner({"status"})

        expression = parse_query("response_time > 1000")

        plan = planner.plan(expression)

        self.assertEqual(
            plan.strategy,
            "FULL_SCAN",
        )

    def test_or_expression_uses_full_scan(self):
        planner = QueryPlanner(
            {"status", "service"}
        )

        expression = parse_query(
            "status = 500 OR service = 'auth'"
        )

        plan = planner.plan(expression)

        self.assertEqual(
            plan.strategy,
            "FULL_SCAN",
        )

    def test_numeric_or_expression_uses_full_scan(self):
        planner = QueryPlanner(
            set(),
            {"response_time"},
        )

        expression = parse_query(
            "response_time > 500 OR response_time < 100"
        )

        plan = planner.plan(expression)

        self.assertEqual(
            plan.strategy,
            "FULL_SCAN",
        )


class TestQueryExecutor(unittest.TestCase):

    def test_indexed_query(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                records = [
                    {"status": 200, "value": "a"},
                    {"status": 500, "value": "b"},
                    {"status": 500, "value": "c"},
                    {"status": 404, "value": "d"},
                ]

                index = HashIndex("status")

                for record in records:
                    record_id = store.append(record)
                    index.add(record_id, record)

                expression = parse_query("status = 500")

                executor = QueryExecutor(
                    store,
                    {"status": index},
                )

                results = list(
                    executor.execute(expression)
                )

                self.assertEqual(
                    [record["value"] for _, record in results],
                    ["b", "c"],
                )

    def test_full_scan_query(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                store.append({"response_time": 100})
                store.append({"response_time": 2000})
                store.append({"response_time": 3000})

                expression = parse_query(
                    "response_time > 1000"
                )

                executor = QueryExecutor(
                    store,
                    {},
                )

                results = list(
                    executor.execute(expression)
                )

                self.assertEqual(
                    len(results),
                    2,
                )

    def test_numeric_index_range_query(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                records = [
                    {"response_time": 100},
                    {"response_time": 200},
                    {"response_time": 200},
                    {"response_time": 500},
                    {"response_time": 1000},
                ]

                numeric_index = NumericIndex("response_time")

                for record in records:
                    record_id = store.append(record)
                    numeric_index.add(record_id, record)

                expression = parse_query(
                    "response_time > 200"
                )

                executor = QueryExecutor(
                    store,
                    {},
                    {"response_time": numeric_index},
                )

                results = list(
                    executor.execute(expression)
                )

                self.assertEqual(
                    [record["response_time"] for _, record in results],
                    [500, 1000],
                )

    def test_numeric_index_matches_full_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                records = [
                    {"response_time": 100},
                    {"response_time": 200},
                    {"response_time": 200},
                    {"response_time": 500},
                    {"response_time": 1000},
                    {"service": "auth"},
                ]

                numeric_index = NumericIndex("response_time")

                for record in records:
                    record_id = store.append(record)
                    numeric_index.add(record_id, record)

                queries = [
                    "response_time > 200",
                    "response_time >= 200",
                    "response_time < 500",
                    "response_time <= 500",
                ]

                indexed_executor = QueryExecutor(
                    store,
                    {},
                    {"response_time": numeric_index},
                )

                full_scan_executor = QueryExecutor(
                    store,
                    {},
                )

                for query in queries:
                    expression = parse_query(query)

                    indexed_ids = {
                        record_id
                        for record_id, _ in
                        indexed_executor.execute(expression)
                    }

                    full_scan_ids = {
                        record_id
                        for record_id, _ in
                        full_scan_executor.execute(expression)
                    }

                    with self.subTest(query=query):
                        self.assertEqual(
                            indexed_ids,
                            full_scan_ids,
                        )

    def test_indexed_and_expression(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                records = [
                    {
                        "status": 500,
                        "response_time": 500,
                    },
                    {
                        "status": 500,
                        "response_time": 2000,
                    },
                    {
                        "status": 200,
                        "response_time": 3000,
                    },
                ]

                index = HashIndex("status")

                for record in records:
                    record_id = store.append(record)
                    index.add(record_id, record)

                expression = parse_query(
                    "status = 500 "
                    "AND response_time > 1000"
                )

                executor = QueryExecutor(
                    store,
                    {"status": index},
                )

                results = list(
                    executor.execute(expression)
                )

                self.assertEqual(
                    len(results),
                    1,
                )

                self.assertEqual(
                    results[0][1]["response_time"],
                    2000,
                )

    def test_or_expression_returns_matches_from_both_branches(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                records = [
                    {"status": 500, "service": "payment"},
                    {"status": 200, "service": "auth"},
                    {"status": 500, "service": "auth"},
                    {"status": 404, "service": "search"},
                ]

                index = HashIndex("status")

                for record in records:
                    record_id = store.append(record)
                    index.add(record_id, record)

                expression = parse_query(
                    "status = 500 OR service = 'auth'"
                )

                executor = QueryExecutor(
                    store,
                    {"status": index},
                )

                results = list(
                    executor.execute(expression)
                )

                self.assertEqual(
                    len(results),
                    3,
                )

    def test_nested_and_or_expression(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                records = [
                    {"status": 500, "response_time": 2000, "service": "payment"},
                    {"status": 500, "response_time": 500, "service": "auth"},
                    {"status": 200, "response_time": 3000, "service": "auth"},
                    {"status": 500, "response_time": 3000, "service": "search"},
                ]

                index = HashIndex("status")

                for record in records:
                    record_id = store.append(record)
                    index.add(record_id, record)

                expression = parse_query(
                    "status = 500 AND "
                    "(response_time > 1000 OR service = 'auth')"
                )

                executor = QueryExecutor(
                    store,
                    {"status": index},
                )

                results = list(executor.execute(expression))

                self.assertEqual(
                    len(results),
                    3,
                )

        def test_nested_or_and_expression(self):
            with tempfile.TemporaryDirectory() as directory:
                with RecordStore(directory) as store:
                    records = [
                        {"status": 500, "service": "auth"},
                        {"status": 404, "service": "auth"},
                        {"status": 500, "service": "payment"},
                        {"status": 200, "service": "auth"},
                    ]

                    index = HashIndex("status")

                    for record in records:
                        record_id = store.append(record)
                        index.add(record_id, record)

                    expression = parse_query(
                        "(status = 500 OR status = 404) "
                        "AND service = 'auth'"
                    )

                    executor = QueryExecutor(
                        store,
                        {"status": index},
                    )

                    results = list(executor.execute(expression))

                    self.assertEqual(
                        len(results),
                        2,
                    )


    def test_sort_ascending(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                records = [
                    {"response_time": 500},
                    {"response_time": 100},
                    {"response_time": 300},
                ]

                for record in records:
                    store.append(record)

                executor = QueryExecutor(store, {})

                results = list(
                    executor.execute(
                        parse_query("response_time > 0"),
                        order_by="response_time",
                    )
                )

                self.assertEqual(
                    [r["response_time"] for _, r in results],
                    [100, 300, 500],
                )

    def test_sort_descending(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                records = [
                    {"response_time": 500},
                    {"response_time": 100},
                    {"response_time": 300},
                ]

                for record in records:
                    store.append(record)

                executor = QueryExecutor(store, {})

                results = list(
                    executor.execute(
                        parse_query("response_time > 0"),
                        order_by="response_time",
                        descending=True,
                    )
                )

                self.assertEqual(
                    [r["response_time"] for _, r in results],
                    [500, 300, 100],
                )

    def test_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                store.append({
                    "status": 500,
                    "service": "payment",
                    "response_time": 2000,
                })

                executor = QueryExecutor(store, {})

                results = list(
                    executor.execute(
                        parse_query("status = 500"),
                        select_fields=["status", "service"],
                    )
                )

                self.assertEqual(
                    results[0][1],
                    {
                        "status": 500,
                        "service": "payment",
                    },
                )

    def test_limit_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                store.append({"status": 500})

                executor = QueryExecutor(store, {})

                results = list(
                    executor.execute(
                        parse_query("status = 500"),
                        limit=0,
                    )
                )

                self.assertEqual(results, [])

    def test_negative_limit_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                store.append({"status": 500})

                executor = QueryExecutor(store, {})

                with self.assertRaises(ValueError):
                    list(
                        executor.execute(
                            parse_query("status = 500"),
                            limit=-1,
                        )
                    )

    def test_none_values_remain_last_when_sorting_descending(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                records = [
                    {"status": 500, "response_time": 200},
                    {"status": 500, "response_time": None},
                    {"status": 500, "response_time": 500},
                    {"status": 500, "response_time": 100},
                ]

                for record in records:
                    store.append(record)

                executor = QueryExecutor(store, {})

                results = list(
                    executor.execute(
                        parse_query("status = 500"),
                        order_by="response_time",
                        descending=True,
                    )
                )

                self.assertEqual(
                    [record["response_time"] for _, record in results],
                    [500, 200, 100, None],
                )


if __name__ == "__main__":
    unittest.main()
