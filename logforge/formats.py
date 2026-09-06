from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator, TextIO

from .errors import ParseError


def normalize_csv_value(value: str | None) -> Any:
    """
    Convert CSV scalar values into useful Python types.

    Examples:

        "42"       -> 42
        "3.14"     -> 3.14
        "true"     -> True
        "false"    -> False
        "null"     -> None
        ""         -> None
        "hello"    -> "hello"
    """

    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    lowered = value.lower()

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    if lowered in {"null", "none"}:
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


class JSONLParser:
    """Streaming JSON Lines parser."""

    def __init__(self, file: TextIO):
        self.file = file

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for line_number, line in enumerate(self.file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ParseError(
                    f"Invalid JSON on line {line_number}: {exc.msg}"
                ) from exc

            if not isinstance(record, dict):
                raise ParseError(
                    f"Line {line_number} must contain a JSON object"
                )

            yield record


class CSVParser:
    """Streaming CSV parser."""

    def __init__(self, file: TextIO):
        self.file = file

    def __iter__(self) -> Iterator[dict[str, Any]]:
        reader = csv.DictReader(self.file)

        if reader.fieldnames is None:
            raise ParseError(
                "CSV file does not contain a header"
            )

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            if None in row:
                raise ParseError(
                    f"Malformed CSV on line {line_number}"
                )

            record = {
                key: normalize_csv_value(value)
                for key, value in row.items()
            }

            yield record


def open_parser(
    path: str | Path,
    format_name: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Open a CSV or JSONL file and return a streaming parser.

    Format is inferred from the file extension unless explicitly provided.
    """

    path = Path(path)

    if not path.exists():
        raise ParseError(
            f"File does not exist: {path}"
        )

    if not path.is_file():
        raise ParseError(
            f"Not a file: {path}"
        )

    if format_name is None:
        suffix = path.suffix.lower()

        if suffix in {".jsonl", ".ndjson"}:
            format_name = "jsonl"

        elif suffix == ".csv":
            format_name = "csv"

        else:
            raise ParseError(
                f"Cannot infer format from extension: {suffix}"
            )

    format_name = format_name.lower()

    file = open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    )

    try:
        if format_name == "jsonl":
            parser = JSONLParser(file)

        elif format_name == "csv":
            parser = CSVParser(file)

        else:
            raise ParseError(
                f"Unsupported format: {format_name}"
            )

        yield from parser

    finally:
        file.close()