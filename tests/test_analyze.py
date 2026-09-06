import json
import tempfile
import unittest
from pathlib import Path

from logforge.database import Database


class TestAnalyze(unittest.TestCase):

    def test_analyze(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "data.jsonl"
            database_path = Path(directory) / "db"

            source.write_text(
                '{"id": 1, "age": 20, "name": "Alice"}\n'
                '{"id": 2, "age": 30, "name": "Bob"}\n',
                encoding="utf-8",
            )

            with Database(database_path) as database:
                result = database.ingest(
                    source,
                    index_fields=["id"],
                    numeric_index_fields=["age"],
                    search_index=True,
                )

            with Database(database_path) as database:
                analysis = database.analyze()

            self.assertEqual(analysis["records"], 2)
            self.assertEqual(analysis["format"], "jsonl")

            self.assertIn("id", analysis["fields"])
            self.assertIn("age", analysis["fields"])
            self.assertIn("name", analysis["fields"])

            self.assertEqual(
                analysis["fields"]["age"]["type"],
                "integer",
            )

            self.assertEqual(
                analysis["fields"]["age"]["min"],
                20,
            )

            self.assertEqual(
                analysis["fields"]["age"]["max"],
                30,
            )

            self.assertEqual(
                analysis["indexes"]["hash"],
                ["id"],
            )

            self.assertEqual(
                analysis["indexes"]["numeric"],
                ["age"],
            )

            self.assertTrue(
                analysis["indexes"]["search"]
            )


if __name__ == "__main__":
    unittest.main()