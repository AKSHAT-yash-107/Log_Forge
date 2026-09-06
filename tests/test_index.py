import unittest

from logforge.index import HashIndex


class TestHashIndex(unittest.TestCase):

    def test_add_and_lookup(self):
        index = HashIndex("status")

        index.add(
            0,
            {"status": 200},
        )

        index.add(
            1,
            {"status": 500},
        )

        index.add(
            2,
            {"status": 500},
        )

        self.assertEqual(
            index.lookup(500),
            {1, 2},
        )

        self.assertEqual(
            index.lookup(200),
            {0},
        )

    def test_missing_value(self):
        index = HashIndex("status")

        index.add(
            0,
            {"status": 200},
        )

        self.assertEqual(
            index.lookup(404),
            set(),
        )

    def test_missing_field(self):
        index = HashIndex("status")

        index.add(
            0,
            {"endpoint": "/api/users"},
        )

        self.assertEqual(
            index.lookup(500),
            set(),
        )

    def test_value_count(self):
        index = HashIndex("status")

        index.add(0, {"status": 200})
        index.add(1, {"status": 500})
        index.add(2, {"status": 500})
        index.add(3, {"status": 404})

        self.assertEqual(
            index.value_count(),
            3,
        )

    def test_record_count(self):
        index = HashIndex("status")

        index.add(0, {"status": 200})
        index.add(1, {"status": 500})
        index.add(2, {"status": 500})

        self.assertEqual(
            index.record_count(),
            3,
        )

    def test_contains(self):
        index = HashIndex("status")

        index.add(0, {"status": 500})

        self.assertTrue(
            index.contains(500)
        )

        self.assertFalse(
            index.contains(404)
        )

    def test_add_many(self):
        index = HashIndex("status")

        records = [
            (0, {"status": 200}),
            (1, {"status": 500}),
            (2, {"status": 500}),
            (3, {"status": 404}),
        ]

        index.add_many(records)

        self.assertEqual(
            index.lookup(500),
            {1, 2},
        )

    def test_save_and_load(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.idx"

            index = HashIndex(
                "status",
                path,
            )

            index.add(1, {"status": 500})
            index.add(2, {"status": 500})
            index.add(3, {"status": 200})

            index.save()

            loaded = HashIndex(
                "status",
                path,
            )

            loaded.load()

            self.assertEqual(
                loaded.lookup(500),
                {1, 2},
            )

            self.assertEqual(
                loaded.lookup(200),
                {3},
            )

    def test_different_types_do_not_collide(self):
        index = HashIndex("value")

        index.add(1, {"value": 500})
        index.add(2, {"value": "500"})

        self.assertEqual(
            index.lookup(500),
            {1},
        )

        self.assertEqual(
            index.lookup("500"),
            {2},
        )

if __name__ == "__main__":
    unittest.main()