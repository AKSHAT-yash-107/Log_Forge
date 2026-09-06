# LogForge

**A zero-dependency local data engine for CSV, JSONL, and log data.**

LogForge is a small, persistent data engine built entirely with the Python standard library. It provides structured ingestion, persistent storage, indexing, filtering, sorting, projection, full-text search, analytics, query planning, and database diagnostics through a CLI.

The goal is not to reproduce a full database system. The goal is to build the important pieces of one clearly, locally, and without third-party runtime dependencies.

## Why LogForge?

LogForge provides a focused local workflow for structured logs and exported datasets:

```text
CSV / JSONL
    ↓
Parser
    ↓
Schema inference
    ↓
Persistent storage
    ↓
Indexes
    ↓
Query planner
    ↓
Query executor
    ↓
Analytics / CLI
```

## Core Features

- CSV and JSONL ingestion
- Automatic schema/type inference
- Append-only persistent record storage
- Offset-based record lookup
- CRC32 record integrity checks
- Recovery of orphaned data tails
- Persistent hash indexes for equality queries
- Persistent numeric indexes for range queries
- Persistent inverted index for full-text search
- Query lexer and parser
- Boolean expressions with `AND`, `OR`, and `NOT`
- Query planning with index selection
- Full-scan fallback
- Field projection
- Ascending and descending sorting
- Result limits
- Numeric statistics
- Group-by analytics
- Query plan explanation
- Database inspection and analysis
- Database health diagnostics
- Index consistency validation
- Standard-library-only runtime

## Installation

LogForge has no `pyproject.toml`/`setup.py` yet, so it isn't pip-installable. Run it directly from the repository root with `PYTHONPATH` set:

```bash
# macOS / Linux
git clone https://github.com/AKSHAT-yash-107/Log_Forge.git
cd Log_Forge
export PYTHONPATH=.
python3 -m logforge --help
```

```powershell
# Windows (PowerShell)
git clone https://github.com/AKSHAT-yash-107/Log_Forge.git
cd Log_Forge
$env:PYTHONPATH = "."
python -m logforge --help
```

Requires Python 3.10+ (uses `from __future__ import annotations` and `X | Y` union syntax throughout).

## Architecture

```text
                         ┌──────────────────┐
                         │    CSV / JSONL    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │     Parsers      │
                         │ CSV / JSONL      │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Schema / Normalize│
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │     Persistent Storage    │
                    │                           │
                    │ records.dat               │
                    │ offsets.dat               │
                    │ metadata.json             │
                    └────────────┬──────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
      ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
      │ Hash Index  │    │ Numeric Index│    │ Inverted     │
      │ equality    │    │ range        │    │ Index / text │
      └──────┬──────┘    └──────┬───────┘    └──────┬───────┘
             │                  │                   │
             └──────────────────┼───────────────────┘
                                ▼
                       ┌─────────────────┐
                       │ Query Planner   │
                       └────────┬────────┘
                                ▼
                       ┌─────────────────┐
                       │ Query Executor  │
                       │ filter / sort   │
                       │ project / limit │
                       └────────┬────────┘
                                ▼
                       ┌─────────────────┐
                       │   Analytics     │
                       │ stats / groupby │
                       └────────┬────────┘
                                ▼
                       ┌─────────────────┐
                       │      CLI        │
                       └─────────────────┘
```

## Storage Design

LogForge uses an append-only record file:

```text
records.dat
┌──────────────┬──────────────┬──────────────┐
│ payload size │ JSON payload │    CRC32     │
└──────────────┴──────────────┴──────────────┘
```

`offsets.dat` stores the byte offset for each committed record. This provides stable integer record IDs, direct lookup, sequential scans, persistence, integrity validation, and recovery of uncommitted data tails.

The storage layer treats offset publication as the record visibility boundary.

## Indexing

### Hash index

Used for equality predicates such as:

```text
status = 500
```

Conceptually:

```text
value → record IDs
```

### Numeric index

Used for numeric range predicates such as:

```text
Age >= 30
Fare < 50
```

Values are maintained in sorted order so range selection can use binary search.

### Inverted index

Used for text search:

```text
search "database timeout"
```

Conceptually:

```text
token → record IDs
```

Search terms are lowercased and intersected for multi-word AND-style search.

## Query Engine

```text
Query text
    ↓
Lexer
    ↓
Parser
    ↓
AST
    ↓
Planner
    ↓
Executor
```

Supported comparisons:

```text
=
!=
>
>=
<
<=
```

Supported boolean operators:

```text
AND
OR
NOT
```

Parentheses are supported.

### Examples

First, ingest the bundled example dataset (see [Ingestion](#ingestion) below) so these commands have something to query.

Equality:

```bash
python -m logforge query --database data/titanic --where "Survived = 1"
```

Range:

```bash
python -m logforge query --database data/titanic --where "Age >= 30"
```

Projection:

```bash
python -m logforge query --database data/titanic --where "Survived = 1" --select Name Age Fare
```

Sorting and limiting:

```bash
python -m logforge query --database data/titanic --where "Survived = 1" --select Name Age Fare --order-by Fare --desc --limit 10
```

## Ingestion

JSONL:

```bash
python -m logforge ingest examples/access.jsonl --database data/logforge --index status --index endpoint
```

CSV:

```bash
python -m logforge ingest examples/titanic.csv --database data/titanic --index Survived --index Pclass --index Sex --numeric-index Age --numeric-index Fare --search
```

`--database` is a target directory LogForge creates on first ingest — it doesn't need to exist beforehand.

## Search

```bash
python -m logforge search --database data/titanic "Braund"
```

Multi-word search:

```bash
python -m logforge search --database data/titanic "Owen Harris"
```

## Analytics

Statistics:

```bash
python -m logforge stats Age --database data/titanic
```

Group-by:

```bash
python -m logforge groupby Pclass --database data/titanic
```

## Query Planning

```bash
python -m logforge explain --database data/titanic --where "Age >= 30"
```

The planner can select:

```text
INDEX_SCAN
NUMERIC_INDEX_SCAN
FULL_SCAN
```

This makes optimization decisions observable.

## Database Diagnostics

Inspect:

```bash
python -m logforge inspect --database data/titanic
```

Analyze:

```bash
python -m logforge analyze --database data/titanic
```

Health check:

```bash
python -m logforge doctor --database data/titanic
```

Example:

```text
LogForge Doctor
────────────────────────
✓ Metadata
✓ Storage
✓ Record count
✓ Hash indexes
✓ Numeric indexes
✓ Search index
────────────────────────
Database is healthy.
```

Doctor also validates basic index invariants, including invalid record IDs and numeric-index structure.

## Reliability

LogForge includes explicit reliability mechanisms:

- Each stored record contains a CRC32 checksum.
- The offset file is validated for complete record offsets.
- Orphaned data after the last committed offset is detected and truncated during recovery.
- Indexes are written to temporary files, synchronized, and atomically replaced.
- Bulk ingestion avoids an `fsync()` for every individual record and performs an explicit store flush after the batch.

## Benchmarks

A synthetic JSONL workload was tested at 10,000, 100,000, and 1,000,000 records.

Measured operations:

1. ingestion
2. hash-index equality query
3. numeric range query
4. full scan
5. full-text search
6. numeric statistics

### Results

| Records | Ingest | Equality | Range | Full Scan | Text Search |
|---:|---:|---:|---:|---:|---:|
| 10K | 0.701s | 0.011s | 0.073s | 0.065s | 0.069s |
| 100K | 4.372s | 0.058s | 0.436s | 0.519s | 1.412s |
| 1M | 38.609s | 0.588s | 4.197s | 4.148s | 5.259s |

The 1-million-record workload completed ingestion and all measured query/analytics operations. Equality uses the hash index, range uses the numeric index, and the full-scan workload intentionally targets a non-indexed field.

Single run per data point, no environment details recorded yet — see `benchmarks/README.md` for a fuller writeup with caveats before citing these numbers externally.

## Testing

The suite covers storage, persistence, corruption detection, recovery, schema inference, CSV/JSONL parsing, all index types, query parsing/evaluation/planning/execution, projection, sorting, limits, analytics, CLI behavior, diagnostics, and index consistency.

Current suite:

```text
113 tests
OK
```

Run it with either runner:

```bash
python -m pytest tests/ -v
# or
python -m unittest discover -s tests -p "test_*.py" -v
```

## Project Structure

```text
Log_Forge/
├── logforge/
│   ├── __main__.py
│   ├── cli.py
│   ├── storage.py
│   ├── formats.py
│   ├── schema.py
│   ├── index.py
│   ├── numeric_index.py
│   ├── index_manager.py
│   ├── query.py
│   ├── evaluator.py
│   ├── executor.py
│   ├── database.py
│   ├── analytics.py
│   ├── search.py
│   ├── errors.py
│   └── metadata.py
├── tests/
├── examples/
└── benchmarks/
```

`data/` in the command examples above is a database directory LogForge creates for you on first `ingest` — it is not part of the repository.


## Installation

Clone the repository:

```bash
git clone https://github.com/AKSHAT-yash-107/Log_Forge.git
cd Log_Forge 
## Dependencies

**Runtime dependencies: none.**

LogForge is intentionally implemented using the Python standard library. It does not require pandas, NumPy, DuckDB, Elasticsearch, FastAPI, Flask, or external indexing/search libraries.

## Design Philosophy

> **Build less. Make every part excellent.**

LogForge prioritizes understandable internals, persistent data structures, explicit query planning, deterministic behavior, reliability, measurable performance, test coverage, and a useful CLI.

It intentionally avoids becoming a generic everything-platform.

## Status

- **Core engine:** Complete
- **Reliability:** Hardened
- **Indexing:** Complete
- **Query engine:** Complete
- **Analytics:** Complete
- **CLI:** Complete
- **Diagnostics:** Complete
- **Benchmarking:** Complete
- **Test suite:** 113 passing
- **Runtime dependencies:** 0

## License

MIT — see `LICENSE`.
