from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_ROOT / "Homebench_dataset" / "test_data.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "data" / "test_cases"
OUTPUT_PATH = OUTPUT_DIR / "homebench_cases.json"


def load_homebench_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def classify_homebench_case(record: dict[str, Any]) -> tuple[str, str]:
    raw_type = str(record.get("type", "")).strip().lower()
    record_id = str(record.get("id", "")).strip().lower()

    if raw_type == "normal":
        if "_multi_" in record_id:
            return "ambiguous", "hard"
        return "normal", "easy"

    if raw_type.startswith("multi") or raw_type.endswith("_mix") or "mix" in raw_type:
        return "error_conflict", "hard"

    if raw_type.startswith("unexist") or raw_type in {
        "unsupported_action",
        "unsupported_attribute",
        "invalid_device",
        "invalid_command",
    }:
        return "error_conflict", "hard"

    if any(keyword in raw_type for keyword in ("ambiguous", "complex", "multi")):
        return "ambiguous", "medium"

    return "ambiguous", "medium"


def convert_record(record: dict[str, Any]) -> dict[str, Any]:
    category, expected_difficulty = classify_homebench_case(record)
    return {
        "input_text": str(record.get("input", "")).strip(),
        "category": category,
        "expected_difficulty": expected_difficulty,
        "source_dataset": "HomeBench",
        "source_file": SOURCE_PATH.name,
        "language": "en",
        "original_id": record.get("id", ""),
        "original_type": record.get("type", ""),
        "home_id": record.get("home_id"),
    }


def convert_homebench_cases(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    seen_inputs: set[str] = set()

    for record in records:
        converted_record = convert_record(record)
        input_text = converted_record["input_text"]
        if not input_text or input_text in seen_inputs:
            continue
        seen_inputs.add(input_text)
        converted.append(converted_record)

    return converted


def main() -> None:
    records = load_homebench_jsonl(SOURCE_PATH)
    converted = convert_homebench_cases(records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(converted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    category_counter = Counter(item["category"] for item in converted)
    difficulty_counter = Counter(item["expected_difficulty"] for item in converted)

    print(f"Loaded HomeBench records: {len(records)}")
    print(f"Converted cases written to: {OUTPUT_PATH}")
    print(f"Converted cases count: {len(converted)}")
    print(f"Category distribution: {dict(category_counter)}")
    print(f"Difficulty distribution: {dict(difficulty_counter)}")


if __name__ == "__main__":
    main()
