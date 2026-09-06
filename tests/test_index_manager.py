import tempfile
import unittest

from logforge.index_manager import IndexManager
from logforge.storage import RecordStore


class TestIndexManager(unittest.TestCase):

    def test_create_search(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = IndexManager(directory)

            index = manager.create_search()

            self.assertIs(
                index,
                manager.inverted_index,
            )

            self.assertEqual(
                index.path,
                manager.directory / "text.idx",
            )

    def test_save_and_load_search_index(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = IndexManager(directory)

            index = manager.create_search()

            index.add(
                1,
                {
                    "Name": "John Smith",
                    "City": "London",
                },
            )

            manager.save_all()

            new_manager = IndexManager(directory)

            new_manager.load_all()

            self.assertIsNotNone(
                new_manager.inverted_index
            )

            results = new_manager.inverted_index.search("John")

            self.assertEqual(
                results,
                {1},
            )



    def test_create_index(self):
        with tempfile.TemporaryDirectory() as directory:

            manager = IndexManager(directory)

            index = manager.create("status")

            self.assertIs(
                manager.get("status"),
                index,
            )

    def test_build_from_store(self):
        with tempfile.TemporaryDirectory() as directory:

            with RecordStore(directory) as store:

                store.append({
                    "status": 200,
                })

                store.append({
                    "status": 500,
                })

                store.append({
                    "status": 500,
                })

                manager = IndexManager(directory)

                manager.build_from_store(
                    store,
                    ["status"],
                )

                index = manager.get("status")

                self.assertIsNotNone(index)

                self.assertEqual(
                    index.lookup(500),
                    {1, 2},
                )

    def test_save_and_load_all(self):
        with tempfile.TemporaryDirectory() as directory:

            manager = IndexManager(directory)

            index = manager.create("status")

            index.add(
                1,
                {"status": 500},
            )

            index.add(
                2,
                {"status": 500},
            )

            manager.save_all()

            new_manager = IndexManager(
                directory
            )

            new_manager.load_all()

            loaded = new_manager.get(
                "status"
            )

            self.assertIsNotNone(loaded)

            self.assertEqual(
                loaded.lookup(500),
                {1, 2},
            )


if __name__ == "__main__":
    unittest.main()