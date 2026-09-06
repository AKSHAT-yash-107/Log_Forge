import unittest

from logforge.evaluator import evaluate
from logforge.query import parse_query


class TestEvaluator(unittest.TestCase):

    def setUp(self):
        self.record = {
            "status": 500,
            "response_time": 1532,
            "endpoint": "/api/orders",
            "active": True,
            "message": "database timeout",
        }

    def evaluate_query(self, query):
        expression = parse_query(query)
        return evaluate(expression, self.record)

    def test_equal(self):
        self.assertTrue(
            self.evaluate_query("status = 500")
        )

    def test_not_equal(self):
        self.assertTrue(
            self.evaluate_query("status != 200")
        )

    def test_greater_than(self):
        self.assertTrue(
            self.evaluate_query(
                "response_time > 1000"
            )
        )

    def test_greater_than_false(self):
        self.assertFalse(
            self.evaluate_query(
                "response_time > 2000"
            )
        )

    def test_less_than(self):
        self.assertTrue(
            self.evaluate_query(
                "response_time < 2000"
            )
        )

    def test_greater_equal(self):
        self.assertTrue(
            self.evaluate_query(
                "response_time >= 1532"
            )
        )

    def test_less_equal(self):
        self.assertTrue(
            self.evaluate_query(
                "response_time <= 1532"
            )
        )

    def test_string(self):
        self.assertTrue(
            self.evaluate_query(
                'endpoint = "/api/orders"'
            )
        )

    def test_boolean(self):
        self.assertTrue(
            self.evaluate_query(
                "active = true"
            )
        )

    def test_and(self):
        self.assertTrue(
            self.evaluate_query(
                "status = 500 "
                "AND response_time > 1000"
            )
        )

    def test_and_false(self):
        self.assertFalse(
            self.evaluate_query(
                "status = 500 "
                "AND response_time > 2000"
            )
        )

    def test_or(self):
        self.assertTrue(
            self.evaluate_query(
                "status = 404 OR status = 500"
            )
        )

    def test_or_false(self):
        self.assertFalse(
            self.evaluate_query(
                "status = 404 OR status = 200"
            )
        )

    def test_not(self):
        self.assertTrue(
            self.evaluate_query(
                "NOT status = 404"
            )
        )

    def test_parentheses(self):
        self.assertTrue(
            self.evaluate_query(
                "(status = 404 OR status = 500) "
                "AND response_time > 1000"
            )
        )

    def test_missing_field(self):
        self.assertFalse(
            self.evaluate_query(
                "missing = 500"
            )
        )

    def test_null(self):
        record = {"value": None}

        expression = parse_query(
            "value = null"
        )

        self.assertTrue(
            evaluate(expression, record)
        )


if __name__ == "__main__":
    unittest.main()