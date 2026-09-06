import tempfile
import unittest
from pathlib import Path

from logforge.search import (
    InvertedIndex,
    tokenize,
)


class TestSearch(unittest.TestCase):

    def test_tokenize(self):

        self.assertEqual(
            tokenize(
                "Database Timeout ERROR"
            ),
            [
                "database",
                "timeout",
                "error",
            ],
        )

    def build_index(self):

        index = InvertedIndex()

        records = [
            (
                0,
                {
                    "message":
                        "database timeout",
                },
            ),
            (
                1,
                {
                    "message":
                        "database connection failed",
                },
            ),
            (
                2,
                {
                    "message":
                        "network timeout",
                },
            ),
        ]

        for record_id, record in records:
            index.add(
                record_id,
                record,
            )

        return index

    def test_lookup(self):

        index = self.build_index()

        self.assertEqual(
            index.lookup("database"),
            {0, 1},
        )

    def test_case_insensitive(self):

        index = self.build_index()

        self.assertEqual(
            index.lookup("DATABASE"),
            {0, 1},
        )

    def test_single_word_search(self):

        index = self.build_index()

        self.assertEqual(
            index.search("timeout"),
            {0, 2},
        )

    def test_multi_word_search(self):

        index = self.build_index()

        self.assertEqual(
            index.search(
                "database timeout"
            ),
            {0},
        )

    def test_unknown_word(self):

        index = self.build_index()

        self.assertEqual(
            index.search("python"),
            set(),
        )

    def test_persistence(self):

        with tempfile.TemporaryDirectory() as directory:

            path = (
                Path(directory)
                / "search.idx"
            )

            index = InvertedIndex(path)

            index.add(
                1,
                {
                    "message":
                        "database timeout"
                },
            )

            index.add(
                2,
                {
                    "message":
                        "network error"
                },
            )

            index.save()

            loaded = InvertedIndex(path)

            loaded.load()

            self.assertEqual(
                loaded.search(
                    "database timeout"
                ),
                {1},
            )


if __name__ == "__main__":
    unittest.main()