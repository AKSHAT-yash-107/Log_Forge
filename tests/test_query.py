import unittest

from logforge.query import (
    And,
    Comparison,
    Not,
    Or,
    QueryLexer,
    parse_query,
)


class TestQueryLexer(unittest.TestCase):

    def test_simple_expression(self):
        tokens = QueryLexer().tokenize(
            "status = 500"
        )

        self.assertEqual(
            tokens[0].type,
            "IDENTIFIER",
        )

        self.assertEqual(
            tokens[0].value,
            "status",
        )

        self.assertEqual(
            tokens[1].type,
            "OP",
        )

        self.assertEqual(
            tokens[2].type,
            "INTEGER",
        )

    def test_complex_expression(self):
        tokens = QueryLexer().tokenize(
            "status = 500 AND response_time > 1000"
        )

        types = [
            token.type
            for token in tokens
        ]

        self.assertEqual(
            types,
            [
                "IDENTIFIER",
                "OP",
                "INTEGER",
                "AND",
                "IDENTIFIER",
                "OP",
                "INTEGER",
                "EOF",
            ],
        )


class TestQueryParser(unittest.TestCase):

    def test_comparison(self):
        ast = parse_query(
            "status = 500"
        )

        self.assertEqual(
            ast,
            Comparison(
                "status",
                "=",
                500,
            ),
        )

    def test_greater_than(self):
        ast = parse_query(
            "response_time > 1000"
        )

        self.assertEqual(
            ast,
            Comparison(
                "response_time",
                ">",
                1000,
            ),
        )

    def test_and(self):
        ast = parse_query(
            "status = 500 AND response_time > 1000"
        )

        self.assertIsInstance(
            ast,
            And,
        )

        self.assertEqual(
            ast.left,
            Comparison(
                "status",
                "=",
                500,
            ),
        )

        self.assertEqual(
            ast.right,
            Comparison(
                "response_time",
                ">",
                1000,
            ),
        )

    def test_or(self):
        ast = parse_query(
            "status = 500 OR status = 404"
        )

        self.assertIsInstance(
            ast,
            Or,
        )

    def test_parentheses(self):
        ast = parse_query(
            "(status = 500 OR status = 404) "
            "AND response_time > 1000"
        )

        self.assertIsInstance(
            ast,
            And,
        )

        self.assertIsInstance(
            ast.left,
            Or,
        )

    def test_not(self):
        ast = parse_query(
            "NOT status = 500"
        )

        self.assertIsInstance(
            ast,
            Not,
        )


if __name__ == "__main__":
    unittest.main()