from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .database import Database
from .errors import LogForgeError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logforge",
        description=(
            "Zero-dependency local data engine "
            "for CSV and JSONL files."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------
    # EXPLAIN
    # --------------------------------------------------

    explain = subparsers.add_parser(
        "explain",
        help="Show the query execution plan.",
    )

    explain.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    explain.add_argument(
        "--where",
        required=True,
        help="Filter expression.",
    )

    # --------------------------------------------------
    # INGEST
    # --------------------------------------------------

    ingest = subparsers.add_parser(
        "ingest",
        help="Ingest a CSV or JSONL file.",
    )

    ingest.add_argument(
        "--numeric-index",
        action="append",
        default=[],
        help=(
            "Numeric field to index for range queries. "
            "Can be specified multiple times."
        ),
    )

    ingest.add_argument(
        "source",
        help="Path to CSV or JSONL file.",
    )

    ingest.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    ingest.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default=None,
        help="Input format. Auto-detected by default.",
    )

    ingest.add_argument(
        "--index",
        action="append",
        default=[],
        help=(
            "Field to index. Can be specified "
            "multiple times."
        ),
    )

    ingest.add_argument(
        "--search",
        action="store_true",
        help="Build a full-text search index.",
    )

    # --------------------------------------------------
    # STATS
    # --------------------------------------------------

    stats = subparsers.add_parser(
        "stats",
        help="Calculate statistics for a numeric field.",
    )

    stats.add_argument(
        "field",
        help="Numeric field.",
    )

    stats.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    # --------------------------------------------------
    # GROUPBY
    # --------------------------------------------------

    groupby = subparsers.add_parser(
        "groupby",
        help="Group records by a field.",
    )

    groupby.add_argument(
        "field",
        help="Field to group by.",
    )

    groupby.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    groupby.add_argument(
        "--avg",
        dest="aggregate_field",
        default=None,
        help="Calculate average/min/max/sum for a numeric field.",
    )

    # --------------------------------------------------
    # INSPECT
    # --------------------------------------------------

    inspect = subparsers.add_parser(
        "inspect",
        help="Inspect database metadata.",
    )

    inspect.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )


    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze database schema, statistics, and indexes.",
    )

    analyze.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )
    # --------------------------------------------------
    # QUERY
    # --------------------------------------------------

    query = subparsers.add_parser(
        "query",
        help="Query stored records.",
    )

    query.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    query.add_argument(
        "--where",
        required=True,
        help="Filter expression.",
    )

    query.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Maximum number of results.",
    )
    query.add_argument(
        "--select",
        nargs="+",
        default=None,
        help="Fields to return.",
    )

    query.add_argument(
        "--order-by",
        default=None,
        help="Field to sort results by.",
    )

    query.add_argument(
        "--desc",
        action="store_true",
        help="Sort in descending order.",
    )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    search = subparsers.add_parser(
        "search",
        help="Search indexed text.",
    )

    search.add_argument(
        "text",
        help="Text to search for.",
    )

    search.add_argument(
        "--database",
        "-d",
        default="data/logforge",
        help="LogForge database directory.",
    )

    search.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Maximum number of results.",
    )

    return parser


def cmd_ingest(args: argparse.Namespace) -> int:

    with Database(args.database) as database:
        result = database.ingest(
            args.source,
            format_name=args.format,
            index_fields=args.index,
            numeric_index_fields=args.numeric_index,
            search_index=args.search,
        )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:

    database_path = Path(args.database)

    if not database_path.exists():
        print(
            f"Database does not exist: "
            f"{database_path}",
            file=sys.stderr,
        )

        return 1

    with Database(database_path) as database:

        metadata = database.inspect()

    print(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0

def cmd_analyze(args: argparse.Namespace) -> int:
    with Database(args.database) as database:
        result = database.analyze()

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0

def cmd_query(args: argparse.Namespace) -> int:
    with Database(args.database) as database:
        results = database.query(
            args.where,
            select_fields=args.select,
            order_by=args.order_by,
            descending=args.desc,
            limit=args.limit,
        )

        for record_id, record in results:
            print(
                json.dumps(
                    {
                        "_id": record_id,
                        **record,
                    },
                    ensure_ascii=False,
                )
            )

    return 0

def cmd_explain(args: argparse.Namespace) -> int:

    with Database(args.database) as database:

        plan = database.explain(
            args.where
        )

    print(
        json.dumps(
            plan,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


def cmd_stats(args: argparse.Namespace) -> int:

    with Database(args.database) as database:

        result = database.stats(
            args.field
        )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


def cmd_groupby(args: argparse.Namespace) -> int:

    with Database(args.database) as database:

        if args.aggregate_field:

            result = database.groupby_numeric(
                args.field,
                args.aggregate_field,
            )

        else:

            result = database.groupby(
                args.field,
            )

    print(
        json.dumps(
            {
                str(key): value
                for key, value in result.items()
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


def cmd_search(args: argparse.Namespace) -> int:

    with Database(args.database) as database:

        results = database.search(
            args.text
        )

        count = 0

        for record_id, record in results:

            print(
                json.dumps(
                    {
                        "_id": record_id,
                        **record,
                    },
                    ensure_ascii=False,
                )
            )

            count += 1

            if (
                args.limit is not None
                and count >= args.limit
            ):
                break

    return 0


def main(argv=None) -> int:

    parser = build_parser()

    args = parser.parse_args(argv)

    try:
        if args.command == "stats":
            return cmd_stats(args)

        if args.command == "groupby":
            return cmd_groupby(args)

        if args.command == "explain":
            return cmd_explain(args)

        if args.command == "ingest":
            return cmd_ingest(args)

        if args.command == "inspect":
            return cmd_inspect(args)

        if args.command == "query":
            return cmd_query(args)

        if args.command == "search":
            return cmd_search(args)
        if args.command == "analyze":
            return cmd_analyze(args)

        parser.error(
            f"Unknown command: {args.command}"
        )

    except LogForgeError as exc:

        print(
            f"LogForge error: {exc}",
            file=sys.stderr,
        )

        return 1

    except (OSError, ValueError) as exc:

        print(
            f"Error: {exc}",
            file=sys.stderr,
        )

        return 1

    return 0