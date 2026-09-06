from __future__ import annotations
from .metadata import MetadataStore
from dataclasses import dataclass
from pathlib import Path

from .formats import open_parser
from .schema import Schema
from .storage import RecordStore


@dataclass
class IngestionResult:
    source: str
    format_name: str
    records_ingested: int
    fields_discovered: int


def detect_format(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()

    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"

    if suffix == ".csv":
        return "csv"

    raise ValueError(
        f"Cannot determine format from file: {path}"
    )


def ingest_file(
    source: str | Path,
    database: str | Path,
    format_name: str | None = None,
) -> IngestionResult:
    """
    Stream a source file into a LogForge database.

    Records are never loaded into memory as a complete dataset.
    """

    source = Path(source)

    if format_name is None:
        format_name = detect_format(source)

    schema = Schema()
    records_ingested = 0

    with RecordStore(database) as store:

        for record in open_parser(
            source,
            format_name,
        ):
            schema.observe(record)
            store.append(record)

            records_ingested += 1

    metadata = {
        "version": 1,
        "source": str(source),
        "format": format_name,
        "schema": schema.to_dict(),
    }

    MetadataStore(database).save(metadata)

    return IngestionResult(
        source=str(source),
        format_name=format_name,
        records_ingested=records_ingested,
        fields_discovered=len(schema.fields),

    )