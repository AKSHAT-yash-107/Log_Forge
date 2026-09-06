import unittest

from logforge.analytics import (
    group_by,
    group_by_numeric,
    numeric_stats,
)


class TestAnalytics(unittest.TestCase):

    def setUp(self):

        self.records = [
            {
                "class": 1,
                "fare": 100.0,
            },
            {
                "class": 1,
                "fare": 200.0,
            },
            {
                "class": 2,
                "fare": 50.0,
            },
            {
                "class": 3,
                "fare": 20.0,
            },
            {
                "class": 3,
                "fare": None,
            },
        ]

    def test_numeric_stats(self):

        result = numeric_stats(
            self.records,
            "fare",
        )

        self.assertEqual(
            result["count"],
            4,
        )

        self.assertEqual(
            result["min"],
            20.0,
        )

        self.assertEqual(
            result["max"],
            200.0,
        )

        self.assertEqual(
            result["sum"],
            370.0,
        )

        self.assertEqual(
            result["avg"],
            92.5,
        )

    def test_group_by(self):

        result = group_by(
            self.records,
            "class",
        )

        self.assertEqual(
            result,
            {
                1: 2,
                2: 1,
                3: 2,
            },
        )

    def test_group_by_numeric(self):

        result = group_by_numeric(
            self.records,
            "class",
            "fare",
        )

        self.assertEqual(
            result[1]["count"],
            2,
        )

        self.assertEqual(
            result[1]["avg"],
            150.0,
        )

        self.assertEqual(
            result[2]["avg"],
            50.0,
        )

        self.assertEqual(
            result[3]["avg"],
            20.0,
        )

    def test_empty_numeric_field(self):

        result = numeric_stats(
            [
                {"name": "Alice"},
                {"name": "Bob"},
            ],
            "age",
        )

        self.assertEqual(
            result["count"],
            0,
        )

        self.assertIsNone(
            result["avg"]
        )


if __name__ == "__main__":
    unittest.main()