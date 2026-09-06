import tempfile
import unittest
from pathlib import Path

from logforge.database import Database


class TestQueryFeatures(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.base = Path(self.temp_dir.name)
        self.source = self.base / "data.jsonl"
        self.database = self.base / "db"

        self.source.write_text(
            '{"id": 1, "name": "Alice", "age": 30, "score": 80}\n'
            '{"id": 2, "name": "Bob", "age": 20, "score": 95}\n'
            '{"id": 3, "name": "Charlie", "age": 40, "score": 70}\n'
            '{"id": 4, "name": "David", "age": 25, "score": 90}\n',
            encoding="utf-8",
        )

        with Database(self.database) as database:
            database.ingest(
                self.source,
                index_fields=["id"],
                numeric_index_fields=["age", "score"],
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_projection(self):
        with Database(self.database) as database:
            results = list(
                database.query(
                    "age >= 20",
                    select_fields=["name", "age"],
                )
            )

        self.assertEqual(len(results), 4)

        record_id, record = results[0]

        self.assertEqual(record_id, 0)
        self.assertEqual(
            record,
            {
                "name": "Alice",
                "age": 30,
            },
        )

    def test_ascending_sort(self):
        with Database(self.database) as database:
            results = list(
                database.query(
                    "age >= 20",
                    order_by="score",
                )
            )

        scores = [
            record["score"]
            for _, record in results
        ]

        self.assertEqual(
            scores,
            [70, 80, 90, 95],
        )

    def test_descending_sort(self):
        with Database(self.database) as database:
            results = list(
                database.query(
                    "age >= 20",
                    order_by="score",
                    descending=True,
                )
            )

        scores = [
            record["score"]
            for _, record in results
        ]

        self.assertEqual(
            scores,
            [95, 90, 80, 70],
        )

    def test_sort_by_missing_field(self):
        with Database(self.database) as database:
            with self.assertRaises(ValueError):
                list(
                    database.query(
                        "age >= 30",
                        order_by="DoesNotExist",
                    )
                )


    def test_limit(self):
        with Database(self.database) as database:
            results = list(
                database.query(
                    "age >= 20",
                    limit=2,
                )
            )

        self.assertEqual(len(results), 2)

    def test_filter_sort_limit_projection(self):
        with Database(self.database) as database:
            results = list(
                database.query(
                    "age >= 25",
                    select_fields=["name", "score"],
                    order_by="score",
                    descending=True,
                    limit=2,
                )
            )

        self.assertEqual(
            results,
            [
                (
                    3,
                    {
                        "name": "David",
                        "score": 90,
                    },
                ),
                (
                    0,
                    {
                        "name": "Alice",
                        "score": 80,
                    },
                ),
            ],
        )

if __name__ == "__main__":
    unittest.main()