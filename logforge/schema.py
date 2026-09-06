from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TYPE_NULL = "null"
TYPE_BOOLEAN = "boolean"
TYPE_INTEGER = "integer"
TYPE_FLOAT = "float"
TYPE_STRING = "string"


def infer_type(value: Any) -> str:
    """
    Infer the LogForge type of a Python value.
    """

    if value is None:
        return TYPE_NULL

    if isinstance(value, bool):
        return TYPE_BOOLEAN

    if isinstance(value, int):
        return TYPE_INTEGER

    if isinstance(value, float):
        return TYPE_FLOAT

    if isinstance(value, str):
        return TYPE_STRING

    return TYPE_STRING


def merge_types(current: str | None, new: str) -> str:
    """
    Merge two observed types into one compatible type.
    """

    if current is None:
        return new

    if current == TYPE_NULL:
        return new

    if new == TYPE_NULL:
        return current

    if current == new:
        return current

    # integer + float → float
    if {
        current,
        new,
    } == {
        TYPE_INTEGER,
        TYPE_FLOAT,
    }:
        return TYPE_FLOAT

    # Anything incompatible becomes string.
    return TYPE_STRING


@dataclass
class FieldProfile:
    name: str
    type_name: str | None = None
    count: int = 0
    null_count: int = 0

    min_value: Any = None
    max_value: Any = None

    _has_numeric_value: bool = field(
        default=False,
        repr=False,
    )

    def observe(self, value: Any) -> None:
        self.count += 1

        value_type = infer_type(value)

        if value is None:
            self.null_count += 1

        self.type_name = merge_types(
            self.type_name,
            value_type,
        )

        if value_type in {
            TYPE_INTEGER,
            TYPE_FLOAT,
        }:
            if not self._has_numeric_value:
                self.min_value = value
                self.max_value = value
                self._has_numeric_value = True
            else:
                self.min_value = min(
                    self.min_value,
                    value,
                )
                self.max_value = max(
                    self.max_value,
                    value,
                )

    @property
    def null_percentage(self) -> float:
        if self.count == 0:
            return 0.0

        return (
            self.null_count / self.count
        ) * 100


@dataclass
class Schema:
    fields: dict[str, FieldProfile] = field(
        default_factory=dict
    )

    record_count: int = 0

    def observe(
        self,
        record: dict[str, Any],
    ) -> None:
        self.record_count += 1

        for field_name, value in record.items():

            if field_name not in self.fields:
                self.fields[field_name] = FieldProfile(
                    name=field_name
                )

            self.fields[field_name].observe(value)

    def to_dict(self) -> dict:
        return {
            "record_count": self.record_count,
            "fields": {
                name: {
                    "type": profile.type_name,
                    "count": profile.count,
                    "null_count": profile.null_count,
                    "null_percentage": profile.null_percentage,
                    "min": profile.min_value,
                    "max": profile.max_value,
                }
                for name, profile in self.fields.items()
            },
        }
    def field_names(self) -> list[str]:
        return list(self.fields.keys())

    def get(self, field_name: str) -> FieldProfile:
        return self.fields[field_name]