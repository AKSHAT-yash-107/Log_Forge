from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .ingest import detect_format
from .formats import open_parser
from .index_manager import IndexManager
from .metadata import MetadataStore
from .query import parse_query
from .schema import Schema
from .storage import RecordStore


class Database:
    """
    High-level LogForge database interface.

    Owns:

    - persistent records
    - metadata
    - indexes
    - query execution
    - full-text search
    """

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

        self.store = RecordStore(
            self.directory
        )

        self.metadata = MetadataStore(
            self.directory
        )

        self.indexes = IndexManager(
            self.directory
        )

    def open(self) -> None:
        self.store.open()

        # Existing indexes are loaded when the
        # database is opened.
        self.indexes.load_all()

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Database":
        self.open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def ingest(
        self,
        source: str | Path,
        format_name: str | None = None,
        index_fields: Iterable[str] = (),
        numeric_index_fields: Iterable[str] = (),
        search_index: bool = False,
    ) -> dict[str, Any]:

        source = Path(source)

        if format_name is None:
            format_name = detect_format(source)

        schema = Schema()

        indexes = []
        numeric_indexes = []

        for field in numeric_index_fields:
            numeric_indexes.append(
                self.indexes.create_numeric(field)
            )

        for field in index_fields:
            indexes.append(
                self.indexes.create(field)
            )

        # Create the inverted index only when requested.
        inverted_index = None

        if search_index:
            inverted_index = self.indexes.create_search()

        records_ingested = 0

        for record in open_parser(
            source,
            format_name,
        ):
            schema.observe(record)

            record_id = self.store.append(
                record
            )

            for index in indexes:
                index.add(
                    record_id,
                    record,
                )

            for index in numeric_indexes:
                index.add(
                    record_id,
                    record,
                )

            if inverted_index is not None:
                inverted_index.add(
                    record_id,
                    record,
                )

            records_ingested += 1

        self.indexes.save_all()

        metadata = {
            "version": 1,
            "source": str(source),
            "format": format_name,
            "schema": schema.to_dict(),
            "indexes": sorted(
                self.indexes.fields()
            ),
        }

        self.metadata.save(metadata)

        return {
            "source": str(source),
            "format": format_name,
            "records_ingested": records_ingested,
            "fields_discovered": len(
                schema.fields
            ),
            "indexes": sorted(
                self.indexes.fields()
            ),
            "search_index": search_index,
        }

    def get(
        self,
        record_id: int,
    ) -> dict[str, Any]:

        return self.store.get(
            record_id
        )

    def search(
        self,
        text: str,
    ) -> list[tuple[int, dict[str, Any]]]:
        """
        Search indexed text and return matching records.

        Returns:
            [(record_id, record), ...]
        """

        inverted_index = self.indexes.inverted_index

        if inverted_index is None:
            raise ValueError(
                "Full-text search index is not available. "
                "Ingest the database with search_index=True."
            )

        record_ids = inverted_index.search(text)

        return [
            (record_id, self.store.get(record_id))
            for record_id in sorted(record_ids)
        ]

    def explain(
        self,
        expression: str,
    ) -> dict[str, Any]:

        from .executor import QueryPlanner

        ast = parse_query(expression)

        planner = QueryPlanner(
            set(
                self.indexes.hash_indexes.keys()
            ),
            set(
                self.indexes.numeric_indexes.keys()
            ),
        )

        plan = planner.plan(ast)

        return {
            "strategy": plan.strategy,
            "index_field": plan.index_field,
            "operator": plan.operator,
            "value": plan.value,
            "reason": plan.reason,
        }

    def count(self) -> int:
        return len(self.store)

    def inspect(self) -> dict[str, Any]:
        return self.metadata.load()


    def analyze(self) -> dict[str, Any]:
        """Return a complete overview of the database."""

        metadata = self.metadata.load()

        schema = metadata.get("schema", {})

        return {
            "source": metadata.get("source"),
            "format": metadata.get("format"),
            "records": self.count(),
            "fields": schema.get("fields", {}),
            "indexes": {
                "hash": sorted(self.indexes.hash_indexes.keys()),
                "numeric": sorted(self.indexes.numeric_indexes.keys()),
                "search": self.indexes.inverted_index is not None,
            },
        }

    def stats(
        self,
        field: str,
    ) -> dict[str, Any]:

        from .analytics import numeric_stats

        records = (
            record
            for _, record in self.store.scan()
        )

        return numeric_stats(
            records,
            field,
        )

    def groupby(
        self,
        field: str,
    ) -> dict[Any, int]:

        from .analytics import group_by

        records = (
            record
            for _, record in self.store.scan()
        )

        return group_by(
            records,
            field,
        )

    def groupby_numeric(
        self,
        group_field: str,
        aggregate_field: str,
    ) -> dict[Any, dict[str, Any]]:

        from .analytics import group_by_numeric

        records = (
            record
            for _, record in self.store.scan()
        )

        return group_by_numeric(
            records,
            group_field,
            aggregate_field,
        )

    def query(
        self,
        expression: str,
    ):

        ast = parse_query(expression)

        from .executor import QueryExecutor

        executor = QueryExecutor(
            self.store,
            self.indexes.hash_indexes,
            self.indexes.numeric_indexes,
        )

        return executor.execute(ast)