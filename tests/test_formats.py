import io
import unittest

from logforge.formats import CSVParser, JSONLParser


class TestJSONLParser(unittest.TestCase):

    def test_valid_jsonl(self):
        data = (
            '{"id": 1, "status": 200}\n'
            '{"id": 2, "status": 500}\n'
            '{"id": 3, "status": 404}\n'
        )

        records = list(JSONLParser(io.StringIO(data)))

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["id"], 1)
        self.assertEqual(records[1]["status"], 500)

    def test_blank_lines_are_ignored(self):
        data = (
            '{"id": 1}\n'
            '\n'
            '{"id": 2}\n'
            '   \n'
            '{"id": 3}\n'
        )

        records = list(JSONLParser(io.StringIO(data)))

        self.assertEqual(len(records), 3)

    def test_json_array_is_rejected(self):
        data = '[1, 2, 3]\n'

        with self.assertRaises(Exception):
            list(JSONLParser(io.StringIO(data)))


class TestCSVParser(unittest.TestCase):
    class TestCSVNormalization(unittest.TestCase):

        def test_integer(self):
            from logforge.formats import normalize_csv_value

            self.assertEqual(
                normalize_csv_value("42"),
                42,
            )

        def test_float(self):
            from logforge.formats import normalize_csv_value

            self.assertEqual(
                normalize_csv_value("3.14"),
                3.14,
            )

        def test_boolean(self):
            from logforge.formats import normalize_csv_value

            self.assertTrue(
                normalize_csv_value("true")
            )

        def test_null(self):
            from logforge.formats import normalize_csv_value

            self.assertIsNone(
                normalize_csv_value("")
            )

        def test_string(self):
            from logforge.formats import normalize_csv_value

            self.assertEqual(
                normalize_csv_value("Titanic"),
                "Titanic",
            )
    def test_valid_csv(self):
        def test_valid_csv(self):
            data = (
                "id,status,endpoint\n"
                "1,200,/api/users\n"
                "2,500,/api/orders\n"
            )

            records = list(CSVParser(io.StringIO(data)))

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["id"], "1")
            self.assertEqual(records[1]["status"], "500")
            self.assertEqual(
                records[1]["endpoint"],
                "/api/orders",
            )


if __name__ == "__main__":
    unittest.main()