from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_gold_records(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if "gold_dsl" in item and isinstance(item.get("gold_dsl"), dict):
            records.append(item)
        else:
            records.append({"input_text": "", "gold_dsl": item})
    return records


def extract_gold_rules(path: str | Path) -> list[dict[str, Any]]:
    return [record["gold_dsl"] for record in load_gold_records(path)]
