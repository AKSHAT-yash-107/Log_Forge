from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


class HashIndex:
    """
    Persistent hash index.

    Maps:

        field value -> record IDs
    """

    def __init__(
        self,
        field: str,
        path: str | Path | None = None,
    ):
        self.field = field
        self.path = Path(path) if path else None

        self._mapping: dict[Any, set[int]] = defaultdict(set)

    def add(
        self,
        record_id: int,
        record: dict[str, Any],
    ) -> None:

        if self.field not in record:
            return

        value = record[self.field]

        self._mapping[self._key(value)].add(record_id)

    def add_many(
        self,
        records: Iterable[tuple[int, dict[str, Any]]],
    ) -> None:

        for record_id, record in records:
            self.add(record_id, record)

    def lookup(self, value: Any) -> set[int]:
        return set(
            self._mapping.get(
                self._key(value),
                set(),
            )
        )

    def contains(self, value: Any) -> bool:
        return self._key(value) in self._mapping

    def value_count(self) -> int:
        return len(self._mapping)

    def record_count(self) -> int:
        return sum(
            len(ids)
            for ids in self._mapping.values()
        )

    def validate(self, record_count: int) -> None:
        """Validate basic hash-index consistency."""

        for record_ids in self._mapping.values():
            for record_id in record_ids:
                if not isinstance(record_id, int):
                    raise ValueError(
                        f"Invalid record ID in hash index: {record_id!r}"
                    )

                if record_id < 0 or record_id >= record_count:
                    raise ValueError(
                        f"Record ID {record_id} is outside "
                        f"database range 0..{record_count - 1}"
                    )

    def clear(self) -> None:
        self._mapping.clear()

    @staticmethod
    def _key(value: Any) -> Any:
        """
        Convert values into JSON-safe dictionary keys.
        """
        if value is None:
            return "__NULL__"

        if isinstance(value, bool):
            return f"__BOOL__:{value}"

        if isinstance(value, (int, float)):
            return f"__NUMBER__:{value}"

        return f"__STRING__:{value}"

    def save(self) -> None:
        if self.path is None:
            raise ValueError("Index path is not configured")

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": 1,
            "field": self.field,
            "mapping": {
                str(key): sorted(record_ids)
                for key, record_ids in self._mapping.items()
            },
        }

        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temporary,
            self.path,
        )

    def load(self) -> None:
        if self.path is None:
            raise ValueError("Index path is not configured")

        with open(
            self.path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if data.get("field") != self.field:
            raise ValueError(
                "Index field does not match index file"
            )

        self._mapping.clear()

        for key, record_ids in data["mapping"].items():
            self._mapping[key] = set(record_ids)