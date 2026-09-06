from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class MetadataStore:

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.path = self.directory / "metadata.json"

    def save(self, metadata: dict[str, Any]) -> None:
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.directory / "metadata.tmp"

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                metadata,
                file,
                indent=2,
                ensure_ascii=False,
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temporary,
            self.path,
        )

    def load(self) -> dict[str, Any]:
        with open(
            self.path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def exists(self) -> bool:
        return self.path.exists()