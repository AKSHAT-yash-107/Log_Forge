import json
import tempfile
import unittest
from pathlib import Path

from logforge.database import Database


class TestExplain(unittest.TestCase):

    def create_database(self, directory):

        source = Path(directory) / "data.jsonl"
        database = Path(directory) / "db"

        source.write_text(
            '{"status":200,"response_time":100}\n'
            '{"status":500,"response_time":1500}\n'
            '{"status":500,"response_time":2200}\n',
            encoding="utf-8",
        )

        with Database(database) as db:
            db.ingest(
                source,
                index_fields=["status"],
            )

        return database

    def test_index_scan_explain(self):

        with tempfile.TemporaryDirectory() as directory:

            database = self.create_database(
                directory
            )

            with Database(database) as db:

                plan = db.explain(
                    "status = 500"
                )

            self.assertEqual(
                plan["strategy"],
                "INDEX_SCAN",
            )

            self.assertEqual(
                plan["index_field"],
                "status",
            )

            self.assertEqual(
                plan["operator"],
                "=",
            )

            self.assertEqual(
                plan["value"],
                500,
            )

    def test_full_scan_explain(self):

        with tempfile.TemporaryDirectory() as directory:

            database = self.create_database(
                directory
            )

            with Database(database) as db:

                plan = db.explain(
                    "response_time > 1000"
                )

            self.assertEqual(
                plan["strategy"],
                "FULL_SCAN",
            )

            self.assertIsNone(
                plan["index_field"]
            )


if __name__ == "__main__":
    unittest.main()