import tempfile
import unittest
from pathlib import Path

from logforge.numeric_index import NumericIndex


class TestNumericIndex(unittest.TestCase):

    def build_index(self):

        index = NumericIndex("age")

        records = [
            (0, {"age": 20}),
            (1, {"age": 30}),
            (2, {"age": 40}),
            (3, {"age": 40}),
            (4, {"age": 50}),
            (5, {"age": 60}),
            (6, {"age": 70}),
        ]

        index.add_many(records)

        return index

    def test_lookup(self):

        index = self.build_index()

        self.assertEqual(
            index.lookup(40),
            {2, 3},
        )

    def test_greater_than(self):

        index = self.build_index()

        self.assertEqual(
            index.greater_than(40),
            {4, 5, 6},
        )

    def test_greater_equal(self):

        index = self.build_index()

        self.assertEqual(
            index.greater_equal(40),
            {2, 3, 4, 5, 6},
        )

    def test_less_than(self):

        index = self.build_index()

        self.assertEqual(
            index.less_than(40),
            {0, 1},
        )

    def test_less_equal(self):

        index = self.build_index()

        self.assertEqual(
            index.less_equal(40),
            {0, 1, 2, 3},
        )

    def test_between(self):

        index = self.build_index()

        self.assertEqual(
            index.between(30, 50),
            {1, 2, 3, 4},
        )

    def test_between_exclusive(self):

        index = self.build_index()

        self.assertEqual(
            index.between(
                30,
                50,
                inclusive=False,
            ),
            {2, 3},
        )

    def test_missing_field(self):

        index = NumericIndex("age")

        index.add(
            1,
            {"name": "Alice"},
        )

        self.assertEqual(
            index.record_count(),
            0,
        )

    def test_string_is_not_numeric(self):

        index = NumericIndex("age")

        index.add(
            1,
            {"age": "40"},
        )

        self.assertEqual(
            index.record_count(),
            0,
        )

    def test_boolean_is_not_numeric(self):

        index = NumericIndex("active")

        index.add(
            1,
            {"active": True},
        )

        self.assertEqual(
            index.record_count(),
            0,
        )

    def test_persistence(self):

        with tempfile.TemporaryDirectory() as directory:

            path = (
                Path(directory)
                / "age.idx"
            )

            index = NumericIndex(
                "age",
                path,
            )

            index.add(
                1,
                {"age": 20},
            )

            index.add(
                2,
                {"age": 60},
            )

            index.add(
                3,
                {"age": 70},
            )

            index.save()

            loaded = NumericIndex(
                "age",
                path,
            )

            loaded.load()

            self.assertEqual(
                loaded.greater_than(50),
                {2, 3},
            )

            self.assertEqual(
                loaded.less_than(50),
                {1},
            )


if __name__ == "__main__":
    unittest.main()