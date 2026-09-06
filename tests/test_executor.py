import tempfile
import unittest

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

        expression = parse_query(
            "status = 500"
        )

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

        expression = parse_query(
            "response_time > 1000"
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
                    index.add(
                        record_id,
                        record,
                    )

                expression = parse_query(
                    "status = 500"
                )

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

                store.append({
                    "response_time": 100
                })

                store.append({
                    "response_time": 2000
                })

                store.append({
                    "response_time": 3000
                })

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
                    index.add(
                        record_id,
                        record,
                    )

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


if __name__ == "__main__":
    unittest.main()