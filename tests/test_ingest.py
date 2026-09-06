import json
import tempfile
import unittest
from pathlib import Path

from logforge.ingest import ingest_file


class TestIngestion(unittest.TestCase):

    def test_jsonl_ingestion(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "database"

            records = [
                {
                    "id": 1,
                    "status": 200,
                },
                {
                    "id": 2,
                    "status": 500,
                },
                {
                    "id": 3,
                    "status": 404,
                },
            ]

            with open(
                source,
                "w",
                encoding="utf-8",
            ) as file:

                for record in records:
                    file.write(
                        json.dumps(record) + "\n"
                    )

            result = ingest_file(
                source,
                database,
            )

            self.assertEqual(
                result.records_ingested,
                3,
            )

            self.assertEqual(
                result.fields_discovered,
                2,
            )

    def test_csv_ingestion(self):
        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.csv"
            database = directory / "database"

            source.write_text(
                "id,status\n"
                "1,200\n"
                "2,500\n"
                "3,404\n",
                encoding="utf-8",
            )

            result = ingest_file(
                source,
                database,
            )

            self.assertEqual(
                result.records_ingested,
                3,
            )

            self.assertEqual(
                result.fields_discovered,
                2,
            )


if __name__ == "__main__":
    unittest.main()