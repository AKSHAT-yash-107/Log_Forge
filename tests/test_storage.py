import tempfile
import unittest

from logforge.storage import RecordStore


class TestRecordStore(unittest.TestCase):

    def test_append_and_get(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                record_id = store.append({
                    "status": 500,
                    "endpoint": "/api/users",
                    "response_time": 1532,
                })

                self.assertEqual(record_id, 0)

                record = store.get(0)

                self.assertEqual(record["status"], 500)
                self.assertEqual(record["endpoint"], "/api/users")
                self.assertEqual(record["response_time"], 1532)

    def test_multiple_records(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                for i in range(100):
                    store.append({
                        "id": i,
                        "value": i * 10,
                    })

                self.assertEqual(len(store), 100)

                self.assertEqual(store.get(0)["id"], 0)
                self.assertEqual(store.get(50)["id"], 50)
                self.assertEqual(store.get(99)["id"], 99)

    def test_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:

                store.append({"id": 1})
                store.append({"id": 2})
                store.append({"id": 3})

                records = list(store.scan())

                self.assertEqual(records[0][0], 0)
                self.assertEqual(records[0][1]["id"], 1)

                self.assertEqual(records[2][0], 2)
                self.assertEqual(records[2][1]["id"], 3)


if __name__ == "__main__":
    unittest.main()