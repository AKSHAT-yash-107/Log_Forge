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

    A record becomes committed only after its offset has been
    successfully written to offsets.dat.
    """

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.data_path = self.directory / "records.dat"
        self.offset_path = self.directory / "offsets.dat"

        self.data_file = None
        self.offset_file = None

    def open(self) -> None:
        """Open storage and recover an incomplete data tail."""

        self.data_file = self._open_file(
            self.data_path
        )

        self.offset_file = self._open_file(
            self.offset_path
        )

        try:
            self._recover()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _open_file(path: Path):
        """
        Open an existing file for read/write or create a new one.
        """

        if path.exists():
            return open(path, "r+b")

        return open(path, "w+b")

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

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if (
            self.data_file is None
            or self.offset_file is None
        ):
            raise StorageError(
                "RecordStore is not open"
            )

    def _recover(self) -> None:
        """
        Recover from an interrupted append.

        offsets.dat defines which records are committed.

        Any bytes in records.dat after the end of the last
        committed record are considered an uncommitted tail
        and are removed.

        Corruption inside a committed record is never silently
        repaired.
        """

        self._ensure_open()

        # --------------------------------------------------
        # Validate offsets.dat size
        # --------------------------------------------------

        offset_size = self.offset_file.seek(
            0,
            os.SEEK_END,
        )

        if (
            offset_size
            % _LENGTH_STRUCT.size
            != 0
        ):
            raise CorruptionError(
                "offsets.dat has an invalid size"
            )

        record_count = (
            offset_size
            // _LENGTH_STRUCT.size
        )

        # --------------------------------------------------
        # No committed records
        # --------------------------------------------------

        if record_count == 0:
            committed_end = 0

        else:
            # --------------------------------------------------
            # Find the last committed record
            # --------------------------------------------------

            last_record_id = record_count - 1

            last_offset = self._get_offset(
                last_record_id
            )

            if last_offset < 0:
                raise CorruptionError(
                    "Invalid negative record offset"
                )

            self.data_file.seek(
                last_offset
            )

            raw_length = self.data_file.read(
                _LENGTH_STRUCT.size
            )

            if (
                len(raw_length)
                != _LENGTH_STRUCT.size
            ):
                raise CorruptionError(
                    f"Missing record length at offset "
                    f"{last_offset}"
                )

            payload_length = _LENGTH_STRUCT.unpack(
                raw_length
            )[0]

            payload = self.data_file.read(
                payload_length
            )

            if (
                len(payload)
                != payload_length
            ):
                raise CorruptionError(
                    f"Truncated record at offset "
                    f"{last_offset}"
                )

            raw_crc = self.data_file.read(
                _CRC_STRUCT.size
            )

            if (
                len(raw_crc)
                != _CRC_STRUCT.size
            ):
                raise CorruptionError(
                    f"Missing checksum at offset "
                    f"{last_offset}"
                )

            stored_crc = _CRC_STRUCT.unpack(
                raw_crc
            )[0]

            actual_crc = zlib.crc32(
                payload
            )

            if stored_crc != actual_crc:
                raise CorruptionError(
                    f"Checksum mismatch for record "
                    f"{last_record_id}"
                )

            committed_end = (
                last_offset
                + _LENGTH_STRUCT.size
                + payload_length
                + _CRC_STRUCT.size
            )

        # --------------------------------------------------
        # Compare physical data size with committed size
        # --------------------------------------------------

        data_size = self.data_file.seek(
            0,
            os.SEEK_END,
        )

        if data_size < committed_end:
            raise CorruptionError(
                "records.dat is shorter than "
                "committed data"
            )

        # --------------------------------------------------
        # Remove uncommitted tail
        # --------------------------------------------------

        if data_size > committed_end:
            self.data_file.truncate(
                committed_end
            )

            self.data_file.flush()

            os.fsync(
                self.data_file.fileno()
            )

    def count(self) -> int:
        """Return number of committed records."""

        self._ensure_open()

        size = self.offset_file.seek(
            0,
            os.SEEK_END,
        )

        if (
            size
            % _LENGTH_STRUCT.size
            != 0
        ):
            raise CorruptionError(
                "offsets.dat has an invalid size"
            )

        return (
            size
            // _LENGTH_STRUCT.size
        )

    def append(
        self,
        record: dict[str, Any],
    ) -> int:
        """
        Append a record and return its record ID.

        The record is made durable before its offset is
        published. Therefore an uncommitted data tail can
        safely be removed during recovery.
        """

        self._ensure_open()

        payload = json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        checksum = zlib.crc32(
            payload
        )

        # --------------------------------------------------
        # Write record
        # --------------------------------------------------

        self.data_file.seek(
            0,
            os.SEEK_END,
        )

        offset = self.data_file.tell()

        self.data_file.write(
            _LENGTH_STRUCT.pack(
                len(payload)
            )
        )

        self.data_file.write(
            payload
        )

        self.data_file.write(
            _CRC_STRUCT.pack(
                checksum
            )
        )

        # Make record durable before publishing offset.
        self.data_file.flush()

        os.fsync(
            self.data_file.fileno()
        )

        # --------------------------------------------------
        # Publish offset
        # --------------------------------------------------

        self.offset_file.seek(
            0,
            os.SEEK_END,
        )

        self.offset_file.write(
            _LENGTH_STRUCT.pack(
                offset
            )
        )

        self.offset_file.flush()

        os.fsync(
            self.offset_file.fileno()
        )

        return self.count() - 1

    def _get_offset(
        self,
        record_id: int,
    ) -> int:

        self._ensure_open()

        if record_id < 0:
            raise IndexError(
                "record_id must be non-negative"
            )

        position = (
            record_id
            * _LENGTH_STRUCT.size
        )

        self.offset_file.seek(
            position
        )

        raw = self.offset_file.read(
            _LENGTH_STRUCT.size
        )

        if (
            len(raw)
            != _LENGTH_STRUCT.size
        ):
            raise IndexError(
                f"record_id does not exist: "
                f"{record_id}"
            )

        return _LENGTH_STRUCT.unpack(
            raw
        )[0]

    def get(
        self,
        record_id: int,
    ) -> dict[str, Any]:
        """Retrieve a record by ID."""

        self._ensure_open()

        offset = self._get_offset(
            record_id
        )

        self.data_file.seek(
            offset
        )

        raw_length = self.data_file.read(
            _LENGTH_STRUCT.size
        )

        if (
            len(raw_length)
            != _LENGTH_STRUCT.size
        ):
            raise CorruptionError(
                f"Missing record length at offset "
                f"{offset}"
            )

        payload_length = _LENGTH_STRUCT.unpack(
            raw_length
        )[0]

        payload = self.data_file.read(
            payload_length
        )

        raw_crc = self.data_file.read(
            _CRC_STRUCT.size
        )

        if (
            len(payload)
            != payload_length
        ):
            raise CorruptionError(
                f"Truncated record at offset "
                f"{offset}"
            )

        if (
            len(raw_crc)
            != _CRC_STRUCT.size
        ):
            raise CorruptionError(
                f"Missing checksum at offset "
                f"{offset}"
            )

        stored_crc = _CRC_STRUCT.unpack(
            raw_crc
        )[0]

        actual_crc = zlib.crc32(
            payload
        )

        if stored_crc != actual_crc:
            raise CorruptionError(
                f"Checksum mismatch for record "
                f"{record_id}"
            )

        try:
            record = json.loads(
                payload.decode("utf-8")
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:

            raise CorruptionError(
                f"Invalid JSON for record "
                f"{record_id}"
            ) from exc

        if not isinstance(
            record,
            dict,
        ):
            raise CorruptionError(
                f"Record {record_id} is not "
                f"a JSON object"
            )

        return record

    def scan(
        self,
    ) -> Iterator[
        tuple[int, dict[str, Any]]
    ]:
        """Yield every stored record in ID order."""

        for record_id in range(
            self.count()
        ):
            yield (
                record_id,
                self.get(record_id),
            )

    def __len__(self) -> int:
        return self.count()