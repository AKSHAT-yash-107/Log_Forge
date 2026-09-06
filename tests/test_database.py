import json
import tempfile
import unittest
from pathlib import Path

from logforge.database import Database


class TestDatabase(unittest.TestCase):

    def create_source(
        self,
        directory,
    ):
        source = Path(directory) / "access.jsonl"

        records = [
            {
                "status": 200,
                "endpoint": "/api/users",
                "response_time": 100,
            },
            {
                "status": 500,
                "endpoint": "/api/orders",
                "response_time": 1500,
            },
            {
                "status": 500,
                "endpoint": "/api/orders",
                "response_time": 2200,
            },
            {
                "status": 404,
                "endpoint": "/api/products",
                "response_time": 300,
            },
        ]

        with open(
            source,
            "w",
            encoding="utf-8",
        ) as file:

            for record in records:
                file.write(
                    json.dumps(record)
                    + "\n"
                )

        return source

    def test_ingest(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = self.create_source(
                directory
            )

            database = directory / "db"

            with Database(database) as db:

                result = db.ingest(
                    source,
                    index_fields=[
                        "status",
                        "endpoint",
                    ],
                )

                self.assertEqual(
                    result["records_ingested"],
                    4,
                )

                self.assertEqual(
                    result["fields_discovered"],
                    3,
                )

                self.assertEqual(
                    result["indexes"],
                    [
                        "endpoint",
                        "status",
                    ],
                )

    def test_database_reopens(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = self.create_source(
                directory
            )

            database = directory / "db"

            with Database(database) as db:

                db.ingest(
                    source,
                    index_fields=["status"],
                )

            # New process/database instance.
            with Database(database) as db:

                self.assertEqual(
                    db.count(),
                    4,
                )

                self.assertEqual(
                    db.indexes.get("status").lookup(500),
                    {1, 2},
                )

    def test_query(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = self.create_source(
                directory
            )

            database = directory / "db"

            with Database(database) as db:

                db.ingest(
                    source,
                    index_fields=[
                        "status",
                    ],
                )

                results = list(
                    db.query(
                        "status = 500"
                    )
                )

                self.assertEqual(
                    len(results),
                    2,
                )

                self.assertEqual(
                    results[0][1]["status"],
                    500,
                )

    def test_compound_query(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = self.create_source(
                directory
            )

            database = directory / "db"

            with Database(database) as db:

                db.ingest(
                    source,
                    index_fields=[
                        "status",
                    ],
                )

                results = list(
                    db.query(
                        "status = 500 "
                        "AND response_time > 2000"
                    )
                )

                self.assertEqual(
                    len(results),
                    1,
                )

                self.assertEqual(
                    results[0][1]["response_time"],
                    2200,
                )


if __name__ == "__main__":
    unittest.main()