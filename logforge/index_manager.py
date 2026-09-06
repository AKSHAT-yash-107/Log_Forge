from __future__ import annotations

from pathlib import Path
from typing import Any

from .index import HashIndex
from .numeric_index import NumericIndex


class IndexManager:
    """Manage LogForge hash and numeric indexes."""

    def __init__(self, database: str | Path):
        self.database = Path(database)
        self.directory = self.database / "indexes"

        self.hash_indexes: dict[str, HashIndex] = {}
        self.numeric_indexes: dict[str, NumericIndex] = {}

    @property
    def indexes(self) -> dict[str, HashIndex]:
        """Backward-compatible access to hash indexes."""
        return self.hash_indexes

    def create(
        self,
        field: str,
    ) -> HashIndex:

        if field in self.hash_indexes:
            return self.hash_indexes[field]

        path = self.directory / f"{field}.idx"

        index = HashIndex(
            field,
            path,
        )

        self.hash_indexes[field] = index

        return index

    def create_numeric(
        self,
        field: str,
    ) -> NumericIndex:

        if field in self.numeric_indexes:
            return self.numeric_indexes[field]

        path = self.directory / f"{field}.numeric.idx"

        index = NumericIndex(
            field,
            path,
        )

        self.numeric_indexes[field] = index

        return index

    def get(
        self,
        field: str,
    ) -> HashIndex | NumericIndex | None:

        if field in self.hash_indexes:
            return self.hash_indexes[field]

        return self.numeric_indexes.get(field)

    def get_hash(
        self,
        field: str,
    ) -> HashIndex | None:

        return self.hash_indexes.get(field)

    def get_numeric(
        self,
        field: str,
    ) -> NumericIndex | None:

        return self.numeric_indexes.get(field)

    def fields(self) -> set[str]:

        return (
            set(self.hash_indexes.keys())
            | set(self.numeric_indexes.keys())
        )

    def save_all(self) -> None:

        for index in self.hash_indexes.values():
            index.save()

        for index in self.numeric_indexes.values():
            index.save()

    def load_all(self) -> None:

        if not self.directory.exists():
            return

        for path in self.directory.glob("*.numeric.idx"):

            field = path.name[
                :-len(".numeric.idx")
            ]

            index = self.create_numeric(field)

            index.load()

        for path in self.directory.glob("*.idx"):

            if path.name.endswith(".numeric.idx"):
                continue

            field = path.stem

            index = self.create(field)

            index.load()

    def build_from_store(
        self,
        store,
        fields: list[str],
    ) -> None:

        for field in fields:
            self.create(field)

        for record_id, record in store.scan():

            for field in fields:
                self.hash_indexes[field].add(
                    record_id,
                    record,
                )

    def build_numeric_from_store(
        self,
        store,
        fields: list[str],
    ) -> None:

        for field in fields:
            self.create_numeric(field)

        for record_id, record in store.scan():

            for field in fields:
                self.numeric_indexes[field].add(
                    record_id,
                    record,
                )