import tempfile
import unittest

from logforge.metadata import MetadataStore


class TestMetadataStore(unittest.TestCase):

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:

            store = MetadataStore(directory)

            metadata = {
                "version": 1,
                "format": "jsonl",
                "schema": {
                    "record_count": 10,
                },
            }

            store.save(metadata)

            self.assertTrue(store.exists())

            loaded = store.load()

            self.assertEqual(
                loaded,
                metadata,
            )


if __name__ == "__main__":
    unittest.main()