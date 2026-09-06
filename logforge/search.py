from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9_]+"
)


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
    ]


class InvertedIndex:
    """
    Persistent inverted index.

    Maps:

        token -> record IDs
    """

    def __init__(
        self,
        path: str | Path | None = None,
    ):
        self.path = Path(path) if path else None

        self._mapping: dict[
            str,
            set[int],
        ] = defaultdict(set)

    def add(
        self,
        record_id: int,
        record: dict[str, Any],
    ) -> None:

        for value in record.values():

            if not isinstance(value, str):
                continue

            for token in tokenize(value):

                self._mapping[token].add(
                    record_id
                )

    def lookup(
        self,
        token: str,
    ) -> set[int]:

        return set(
            self._mapping.get(
                token.lower(),
                set(),
            )
        )

    def search(
        self,
        text: str,
    ) -> set[int]:

        tokens = tokenize(text)

        if not tokens:
            return set()

        posting_lists = [
            self.lookup(token)
            for token in tokens
        ]

        if any(
            not posting_list
            for posting_list in posting_lists
        ):
            return set()

        posting_lists.sort(
            key=len
        )

        result = set(
            posting_lists[0]
        )

        for posting_list in posting_lists[1:]:
            result.intersection_update(
                posting_list
            )

            if not result:
                break

        return result

    def token_count(self) -> int:
        return len(self._mapping)

    def record_count(self) -> int:
        return len(
            {
                record_id
                for record_ids in self._mapping.values()
                for record_id in record_ids
            }
        )

    def validate(self, record_count: int) -> None:
        """Validate basic inverted-index consistency."""

        for token, record_ids in self._mapping.items():
            if not isinstance(token, str):
                raise ValueError(
                    f"Invalid token in search index: {token!r}"
                )

            for record_id in record_ids:
                if not isinstance(record_id, int):
                    raise ValueError(
                        f"Invalid record ID in search index: {record_id!r}"
                    )

                if record_id < 0 or record_id >= record_count:
                    raise ValueError(
                        f"Record ID {record_id} is outside "
                        f"database range 0..{record_count - 1}"
                    )

    def clear(self) -> None:
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
            "mapping": {
                token: sorted(record_ids)
                for token, record_ids
                in self._mapping.items()
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
            raise ValueError(
                "Index path is not configured"
            )

        with open(
            self.path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if data.get("version") != 1:
            raise ValueError(
                "Unsupported inverted index version"
            )

        self.clear()

        for token, record_ids in data["mapping"].items():
            self._mapping[token] = set(
                record_ids
            )
            