import tempfile
import unittest

from logforge.storage import RecordStore

import json
import os
import struct
import zlib
from logforge.errors import CorruptionError
from logforge.storage import (
    RecordStore,
    _CRC_STRUCT,
    _LENGTH_STRUCT,
)

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

    def test_reopen_persists_records(self):
        with tempfile.TemporaryDirectory() as directory:

            with RecordStore(directory) as store:
                store.append({"id": 1})
                store.append({"id": 2})

            with RecordStore(directory) as store:
                self.assertEqual(len(store), 2)
                self.assertEqual(
                    store.get(0)["id"],
                    1,
                )
                self.assertEqual(
                    store.get(1)["id"],
                    2,
                )

    def test_corrupted_record_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                store.append({"id": 1})

            data_path = f"{directory}/records.dat"

            with open(data_path, "r+b") as file:
                raw = bytearray(file.read())

                raw[9] ^= 0xFF

                file.seek(0)
                file.write(raw)
                file.truncate()

            with self.assertRaises(CorruptionError):
                with RecordStore(directory):
                    pass

    def test_invalid_offsets_file_size(self):
        with tempfile.TemporaryDirectory() as directory:
            with RecordStore(directory) as store:
                store.append({"id": 1})

            offset_path = f"{directory}/offsets.dat"

            with open(offset_path, "ab") as file:
                file.write(b"\x00")

            with self.assertRaises(CorruptionError):
                with RecordStore(directory):
                    pass


    def test_recover_orphaned_data_tail(self):
        with tempfile.TemporaryDirectory() as directory:

            with RecordStore(directory) as store:

                store.append({"id": 1})

                valid_end = store.data_file.seek(
                    0,
                    2,
                )

                # Simulate a crash after a record was
                # written to records.dat but before its
                # offset was published.
                payload = b'{"id":2}'
                checksum = zlib.crc32(payload)

                store.data_file.write(
                    _LENGTH_STRUCT.pack(len(payload))
                )
                store.data_file.write(payload)
                store.data_file.write(
                    _CRC_STRUCT.pack(checksum)
                )

                store.data_file.flush()

            with RecordStore(directory) as store:

                # The orphaned record must not become
                # visible as a valid LogForge record.
                self.assertEqual(
                    len(store),
                    1,
                )

                self.assertEqual(
                    store.get(0)["id"],
                    1,
                )

                self.assertEqual(
                    store.data_file.seek(0, 2),
                    valid_end,
                )



if __name__ == "__main__":
    unittest.main()