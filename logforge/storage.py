from __future__ import annotations

import json
import os
import struct
import zlib
from pathlib import Path
from typing import Any, Iterator

from .errors import CorruptionError, StorageError


_LENGTH_STRUCT = struct.Struct(">Q")
_CRC_STRUCT = struct.Struct(">I")


class RecordStore:
    """
    Append-only persistent record store.

    Each record is stored as:

        [8-byte payload length]
        [JSON payload]
        [4-byte CRC32]

    offsets.dat stores one 8-byte file offset per record.
    """

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

        self.data_path = self.directory / "records.dat"
        self.offset_path = self.directory / "offsets.dat"

        self.data_file = None
        self.offset_file = None

    def open(self) -> None:
        """Open storage files for reading and appending."""

        self.data_file = open(self.data_path, "a+b")
        self.offset_file = open(self.offset_path, "a+b")

    def close(self) -> None:
        """Close storage files."""

        if self.data_file is not None:
            self.data_file.close()
            self.data_file = None

        if self.offset_file is not None:
            self.offset_file.close()
            self.offset_file = None

    def __enter__(self) -> "RecordStore":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self.data_file is None or self.offset_file is None:
            raise StorageError("RecordStore is not open")

    def count(self) -> int:
        """Return number of indexed records."""

        self._ensure_open()

        self.offset_file.seek(0, os.SEEK_END)
        size = self.offset_file.tell()

        if size % _LENGTH_STRUCT.size != 0:
            raise CorruptionError("offsets.dat has an invalid size")

        return size // _LENGTH_STRUCT.size

    def append(self, record: dict[str, Any]) -> int:
        """
        Append a record and return its record ID.
        """

        self._ensure_open()

        payload = json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        checksum = zlib.crc32(payload)

        # Write record to data file.
        self.data_file.seek(0, os.SEEK_END)
        offset = self.data_file.tell()

        self.data_file.write(_LENGTH_STRUCT.pack(len(payload)))
        self.data_file.write(payload)
        self.data_file.write(_CRC_STRUCT.pack(checksum))

        # Make the record durable before publishing its offset.
        self.data_file.flush()
        os.fsync(self.data_file.fileno())

        # Publish the offset.
        self.offset_file.seek(0, os.SEEK_END)
        self.offset_file.write(_LENGTH_STRUCT.pack(offset))

        self.offset_file.flush()
        os.fsync(self.offset_file.fileno())

        return self.count() - 1

    def _get_offset(self, record_id: int) -> int:
        self._ensure_open()

        if record_id < 0:
            raise IndexError("record_id must be non-negative")

        position = record_id * _LENGTH_STRUCT.size

        self.offset_file.seek(position)
        raw = self.offset_file.read(_LENGTH_STRUCT.size)

        if len(raw) != _LENGTH_STRUCT.size:
            raise IndexError(f"record_id does not exist: {record_id}")

        return _LENGTH_STRUCT.unpack(raw)[0]

    def get(self, record_id: int) -> dict[str, Any]:
        """Retrieve a record by ID."""

        self._ensure_open()

        offset = self._get_offset(record_id)

        self.data_file.seek(offset)

        raw_length = self.data_file.read(_LENGTH_STRUCT.size)

        if len(raw_length) != _LENGTH_STRUCT.size:
            raise CorruptionError(
                f"Missing record length at offset {offset}"
            )

        payload_length = _LENGTH_STRUCT.unpack(raw_length)[0]

        payload = self.data_file.read(payload_length)
        raw_crc = self.data_file.read(_CRC_STRUCT.size)

        if len(payload) != payload_length:
            raise CorruptionError(
                f"Truncated record at offset {offset}"
            )

        if len(raw_crc) != _CRC_STRUCT.size:
            raise CorruptionError(
                f"Missing checksum at offset {offset}"
            )

        stored_crc = _CRC_STRUCT.unpack(raw_crc)[0]
        actual_crc = zlib.crc32(payload)

        if stored_crc != actual_crc:
            raise CorruptionError(
                f"Checksum mismatch for record {record_id}"
            )

        try:
            record = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CorruptionError(
                f"Invalid JSON for record {record_id}"
            ) from exc

        if not isinstance(record, dict):
            raise CorruptionError(
                f"Record {record_id} is not a JSON object"
            )

        return record

    def scan(self) -> Iterator[tuple[int, dict[str, Any]]]:
        """Yield every stored record in record-ID order."""

        for record_id in range(self.count()):
            yield record_id, self.get(record_id)

    def __len__(self) -> int:
        return self.count()