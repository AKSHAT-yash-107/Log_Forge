from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from logforge.database import Database


SIZES = [10_000, 100_000, 1_000_000]


def generate_dataset(path: Path, count: int) -> None:
    with path.open("w", encoding="utf-8") as file:
        for i in range(count):
            record = {
                "id": i,
                "status": 200 if i % 10 else 500,
                "value": i % 1000,
                "message": f"request user_{i % 1000} completed",
            }

            file.write(json.dumps(record))
            file.write("\n")


def measure(function):
    start = time.perf_counter()
    result = function()
    elapsed = time.perf_counter() - start
    return elapsed, result


def run_benchmark(size: int) -> dict:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        source = base / "dataset.jsonl"
        database_path = base / "database"

        print(f"\nGenerating {size:,} records...")
        generation_time, _ = measure(
            lambda: generate_dataset(source, size)
        )

        with Database(database_path) as database:
            ingest_time, _ = measure(
                lambda: database.ingest(
                    source,
                    index_fields=["id", "status"],
                    numeric_index_fields=["value"],
                    search_index=True,
                )
            )

        with Database(database_path) as database:

            equality_time, equality_results = measure(
                lambda: list(
                    database.query("status = 500")
                )
            )

            range_time, range_results = measure(
                lambda: list(
                    database.query("value >= 900")
                )
            )

            full_scan_time, full_scan_results = measure(
                lambda: list(
                    database.query("message = 'request user_999 completed'")
                )
            )

            search_time, search_results = measure(
                lambda: database.search("completed")
            )

            stats_time, stats_result = measure(
                lambda: database.stats("value")
            )

        return {
            "records": size,
            "generation_seconds": round(generation_time, 4),
            "ingest_seconds": round(ingest_time, 4),
            "equality_query_seconds": round(equality_time, 4),
            "equality_results": len(equality_results),
            "range_query_seconds": round(range_time, 4),
            "range_results": len(range_results),
            "full_scan_seconds": round(full_scan_time, 4),
            "full_scan_results": len(full_scan_results),
            "text_search_seconds": round(search_time, 4),
            "text_search_results": len(search_results),
            "stats_seconds": round(stats_time, 4),
            "stats": stats_result,
        }

    output = Path("benchmarks/results.json")
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
def main() -> None:
    results = []

    for size in SIZES:
        result = run_benchmark(size)
        results.append(result)

        print(json.dumps(result, indent=2))

    output = Path("benchmarks/results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {output}")


if __name__ == "__main__":
    main()