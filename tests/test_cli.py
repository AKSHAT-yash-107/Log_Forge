import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from logforge.cli import main


class TestCLI(unittest.TestCase):

    def test_ingest_command(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"status":200,"endpoint":"/users"}\n'
                '{"status":500,"endpoint":"/orders"}\n',
                encoding="utf-8",
            )

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "ingest",
                    str(source),
                    "--database",
                    str(database),
                    "--index",
                    "status",
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            result = json.loads(
                output.getvalue()
            )

            self.assertEqual(
                result["records_ingested"],
                2,
            )

    def test_inspect_command(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"status":200}\n'
                '{"status":500}\n',
                encoding="utf-8",
            )

            main([
                "ingest",
                str(source),
                "--database",
                str(database),
            ])

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "inspect",
                    "--database",
                    str(database),
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            result = json.loads(
                output.getvalue()
            )

            self.assertEqual(
                result["schema"]["record_count"],
                2,
            )

    def test_query_command(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"status":200}\n'
                '{"status":500}\n'
                '{"status":500}\n',
                encoding="utf-8",
            )

            main([
                "ingest",
                str(source),
                "--database",
                str(database),
                "--index",
                "status",
            ])

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "query",
                    "--database",
                    str(database),
                    "--where",
                    "status = 500",
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            lines = output.getvalue().splitlines()

            self.assertEqual(
                len(lines),
                2,
            )

            records = [
                json.loads(line)
                for line in lines
            ]

            self.assertEqual(
                records[0]["status"],
                500,
            )

    def test_query_limit(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"status":500}\n'
                '{"status":500}\n'
                '{"status":500}\n',
                encoding="utf-8",
            )

            main([
                "ingest",
                str(source),
                "--database",
                str(database),
                "--index",
                "status",
            ])

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "query",
                    "--database",
                    str(database),
                    "--where",
                    "status = 500",
                    "--limit",
                    "2",
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            self.assertEqual(
                len(output.getvalue().splitlines()),
                2,
            )


    def test_search_command(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"Name":"John Smith","City":"London"}\n'
                '{"Name":"Alice Brown","City":"Paris"}\n'
                '{"Name":"John Doe","City":"Berlin"}\n',
                encoding="utf-8",
            )

            main([
                "ingest",
                str(source),
                "--database",
                str(database),
                "--search",
            ])

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "search",
                    "--database",
                    str(database),
                    "John",
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            lines = output.getvalue().splitlines()

            self.assertEqual(
                len(lines),
                2,
            )

            records = [
                json.loads(line)
                for line in lines
            ]

            self.assertEqual(
                records[0]["_id"],
                0,
            )

            self.assertEqual(
                records[1]["_id"],
                2,
            )


    def test_search_limit(self):

        with tempfile.TemporaryDirectory() as directory:

            directory = Path(directory)

            source = directory / "data.jsonl"
            database = directory / "db"

            source.write_text(
                '{"Name":"John Smith"}\n'
                '{"Name":"John Doe"}\n'
                '{"Name":"John Brown"}\n',
                encoding="utf-8",
            )

            main([
                "ingest",
                str(source),
                "--database",
                str(database),
                "--search",
            ])

            output = io.StringIO()

            with redirect_stdout(output):

                exit_code = main([
                    "search",
                    "--database",
                    str(database),
                    "John",
                    "--limit",
                    "2",
                ])

            self.assertEqual(
                exit_code,
                0,
            )

            self.assertEqual(
                len(output.getvalue().splitlines()),
                2,
            )


if __name__ == "__main__":
    unittest.main()