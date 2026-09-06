import json
import tempfile
import unittest
from pathlib import Path

from logforge.database import Database


class TestDoctor(unittest.TestCase):

    def test_healthy_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            source = root / "data.jsonl"
            database_path = root / "database"

            source.write_text(
                "\n".join(
                    [
                        json.dumps({
                            "id": 1,
                            "status": 200,
                            "value": 10,
                        }),
                        json.dumps({
                            "id": 2,
                            "status": 500,
                            "value": 20,
                        }),
                    ]
                ),
                encoding="utf-8",
            )

            with Database(database_path) as database:
                database.ingest(
                    source,
                    index_fields=["status"],
                    numeric_index_fields=["value"],
                )

            with Database(database_path) as database:
                result = database.doctor()

            self.assertTrue(result["healthy"])

            statuses = {
                check["name"]: check["status"]
                for check in result["checks"]
            }

            self.assertEqual(statuses["Metadata"], "ok")
            self.assertEqual(statuses["Storage"], "ok")
            self.assertEqual(statuses["Record count"], "ok")
            self.assertEqual(statuses["Hash indexes"], "ok")
            self.assertEqual(statuses["Numeric indexes"], "ok")

    def test_detects_invalid_numeric_record_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            source = root / "data.jsonl"
            database_path = root / "database"

            source.write_text(
                json.dumps({"value": 10}) + "\n",
                encoding="utf-8",
            )

            with Database(database_path) as database:
                database.ingest(
                    source,
                    numeric_index_fields=["value"],
                )

            with Database(database_path) as database:
                database.indexes.numeric_indexes["value"]._mapping[
                    10
                ].add(999)

                result = database.doctor()

            self.assertFalse(result["healthy"])

            numeric_check = next(
                check
                for check in result["checks"]
                if check["name"] == "Numeric indexes"
            )

            self.assertEqual(
                numeric_check["status"],
                "error",
            )

    def test_detects_invalid_hash_record_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            source = root / "data.jsonl"
            database_path = root / "database"

            source.write_text(
                json.dumps({"status": 200}) + "\n",
                encoding="utf-8",
            )

            with Database(database_path) as database:
                database.ingest(
                    source,
                    index_fields=["status"],
                )

            with Database(database_path) as database:
                database.indexes.hash_indexes["status"]._mapping[
                    "__NUMBER__:200"
                ].add(999)

                result = database.doctor()

            self.assertFalse(result["healthy"])

            hash_check = next(
                check
                for check in result["checks"]
                if check["name"] == "Hash indexes"
            )

            self.assertEqual(hash_check["status"], "error")
if __name__ == "__main__":
    unittest.main()