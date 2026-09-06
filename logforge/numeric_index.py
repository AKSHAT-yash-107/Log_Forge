from __future__ import annotations

import bisect
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


class NumericIndex:
    """
    Persistent ordered index for numeric fields.

    Maps:

        numeric value -> record IDs

    The values are maintained in sorted order so that
    range queries can use binary search.
    """

    def __init__(
        self,
        field: str,
        path: str | Path | None = None,
    ):
        self.field = field
        self.path = Path(path) if path else None

        self._values: list[float | int] = []
        self._mapping: dict[float | int, set[int]] = defaultdict(set)

    def add(
        self,
        record_id: int,
        record: dict[str, Any],
    ) -> None:

        if self.field not in record:
            return

        value = record[self.field]

        if not self._is_numeric(value):
            return

        if value not in self._mapping:
            bisect.insort(self._values, value)

        self._mapping[value].add(record_id)

    def add_many(
        self,
        records,
    ) -> None:

        for record_id, record in records:
            self.add(record_id, record)

    def lookup(
        self,
        value: int | float,
    ) -> set[int]:

        if not self._is_numeric(value):
            return set()

        return set(
            self._mapping.get(
                value,
                set(),
            )
        )

    def greater_than(
        self,
        value: int | float,
    ) -> set[int]:

        position = bisect.bisect_right(
            self._values,
            value,
        )

        return self._ids_from_values(
            self._values[position:]
        )

    def greater_equal(
        self,
        value: int | float,
    ) -> set[int]:

        position = bisect.bisect_left(
            self._values,
            value,
        )

        return self._ids_from_values(
            self._values[position:]
        )

    def less_than(
        self,
        value: int | float,
    ) -> set[int]:

        position = bisect.bisect_left(
            self._values,
            value,
        )

        return self._ids_from_values(
            self._values[:position]
        )

    def less_equal(
        self,
        value: int | float,
    ) -> set[int]:

        position = bisect.bisect_right(
            self._values,
            value,
        )

        return self._ids_from_values(
            self._values[:position]
        )

    def between(
        self,
        lower: int | float,
        upper: int | float,
        inclusive: bool = True,
    ) -> set[int]:

        if inclusive:
            start = bisect.bisect_left(
                self._values,
                lower,
            )

            end = bisect.bisect_right(
                self._values,
                upper,
            )

        else:
            start = bisect.bisect_right(
                self._values,
                lower,
            )

            end = bisect.bisect_left(
                self._values,
                upper,
            )

        return self._ids_from_values(
            self._values[start:end]
        )

    def value_count(self) -> int:
        return len(self._values)

    def record_count(self) -> int:
        return sum(
            len(ids)
            for ids in self._mapping.values()
        )

    def validate(self, record_count: int) -> None:
        """Validate basic numeric-index consistency."""

        if self._values != sorted(self._values):
            raise ValueError("Numeric index values are not sorted")

        if len(self._values) != len(set(self._values)):
            raise ValueError("Numeric index contains duplicate values")

        for value in self._values:
            if not self._is_numeric(value):
                raise ValueError(
                    f"Invalid numeric index value: {value!r}"
                )

            if value not in self._mapping:
                raise ValueError(
                    f"Missing mapping for numeric value: {value!r}"
                )

            for record_id in self._mapping[value]:
                if not isinstance(record_id, int):
                    raise ValueError(
                        f"Invalid record ID in numeric index: {record_id!r}"
                    )

                if record_id < 0 or record_id >= record_count:
                    raise ValueError(
                        f"Record ID {record_id} is outside "
                        f"database range 0..{record_count - 1}"
                    )

    def clear(self) -> None:
        self._values.clear()
        self._mapping.clear()

    def save(self) -> None:

        if self.path is None:
            raise ValueError(
                "Index path is not configured"
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": 1,
            "field": self.field,
            "values": [
                {
                    "value": value,
                    "record_ids": sorted(
                        self._mapping[value]
                    ),
                }
                for value in self._values
            ],
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
            raise ValueError(
                "Index path is not configured"
            )

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

        if data.get("version") != 1:
            raise ValueError(
                "Unsupported numeric index version"
            )

        self.clear()

        for entry in data["values"]:

            value = entry["value"]

            self._values.append(
                value
            )

            self._mapping[value] = set(
                entry["record_ids"]
            )

    def _ids_from_values(
        self,
        values: list[int | float],
    ) -> set[int]:

        result: set[int] = set()

        for value in values:
            result.update(
                self._mapping[value]
            )

        return result

    @staticmethod
    def _is_numeric(value: Any) -> bool:

        if isinstance(value, bool):
            return False

        if not isinstance(
            value,
            (int, float),
        ):
            return False

        if isinstance(value, float) and math.isnan(value):
            return False

        return True