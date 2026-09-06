import unittest

from logforge.schema import (
    FieldProfile,
    Schema,
    infer_type,
    merge_types,
)


class TestTypeInference(unittest.TestCase):

    def test_integers(self):
        self.assertEqual(
            infer_type(10),
            "integer",
        )

    def test_float(self):
        self.assertEqual(
            infer_type(10.5),
            "float",
        )

    def test_boolean(self):
        self.assertEqual(
            infer_type(True),
            "boolean",
        )

    def test_string(self):
        self.assertEqual(
            infer_type("hello"),
            "string",
        )

    def test_null(self):
        self.assertEqual(
            infer_type(None),
            "null",
        )


class TestTypeMerging(unittest.TestCase):

    def test_same_type(self):
        self.assertEqual(
            merge_types("integer", "integer"),
            "integer",
        )

    def test_integer_float(self):
        self.assertEqual(
            merge_types("integer", "float"),
            "float",
        )

    def test_incompatible_types(self):
        self.assertEqual(
            merge_types("integer", "string"),
            "string",
        )

    def test_null_does_not_override_type(self):
        self.assertEqual(
            merge_types("integer", "null"),
            "integer",
        )


class TestFieldProfile(unittest.TestCase):

    def test_numeric_statistics(self):
        field = FieldProfile("response_time")

        field.observe(100)
        field.observe(250)
        field.observe(50)

        self.assertEqual(field.type_name, "integer")
        self.assertEqual(field.count, 3)
        self.assertEqual(field.min_value, 50)
        self.assertEqual(field.max_value, 250)

    def test_null_count(self):
        field = FieldProfile("status")

        field.observe(200)
        field.observe(None)
        field.observe(500)

        self.assertEqual(field.null_count, 1)
        self.assertAlmostEqual(
            field.null_percentage,
            33.333333,
            places=4,
        )


class TestSchema(unittest.TestCase):

    def test_schema_observation(self):
        schema = Schema()

        schema.observe({
            "status": 200,
            "response_time": 100,
        })

        schema.observe({
            "status": 500,
            "response_time": 250,
        })

        self.assertEqual(
            schema.record_count,
            2,
        )

        self.assertEqual(
            schema.get("status").type_name,
            "integer",
        )

        self.assertEqual(
            schema.get("response_time").max_value,
            250,
        )


if __name__ == "__main__":
    unittest.main()