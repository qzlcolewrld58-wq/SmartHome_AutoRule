from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.data_utils import load_gold_records
from core.metric_utils import (
    classification_metrics,
    exact_match,
    extract_entities,
    extract_trigger_type,
    field_accuracy,
    multilabel_micro_prf,
    rate,
    safe_div,
)
from core.pipeline import process_rule
from mock_llm_client import MockLLMClient


PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_PATH = PROJECT_ROOT / "data" / "gold_dsl.json"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORT_PATH = REPORT_DIR / "structured_accuracy_report.md"


def load_eval_cases() -> list[dict[str, Any]]:
    return load_gold_records(EVAL_PATH)


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    client = MockLLMClient()
    rows: list[dict[str, Any]] = []

    trigger_preds: list[str | None] = []
    trigger_golds: list[str | None] = []
    entity_pred_sets: list[set[str]] = []
    entity_gold_sets: list[set[str]] = []

    for case in cases:
        gold_dsl = case["gold_dsl"]
        predicted_dsl = process_rule(case["input_text"], client).get("repaired_dsl", {})

        rows.append(
            {
                "exact_match": exact_match(predicted_dsl, gold_dsl),
                "field_accuracy": field_accuracy(predicted_dsl, gold_dsl),
            }
        )

        trigger_preds.append(extract_trigger_type(predicted_dsl))
        trigger_golds.append(extract_trigger_type(gold_dsl))
        entity_pred_sets.append(extract_entities(predicted_dsl))
        entity_gold_sets.append(extract_entities(gold_dsl))

    trigger_metrics = classification_metrics(trigger_preds, trigger_golds, {"time", "state_change", "event"})
    entity_prf = multilabel_micro_prf(entity_pred_sets, entity_gold_sets)

    summary = {
        "sample_count": len(rows),
        "exact_match_rate": rate(sum(1 for row in rows if row["exact_match"]), len(rows)),
        "field_accuracy": f"{safe_div(sum(row['field_accuracy'] for row in rows), len(rows)):.4f}",
        "trigger_type_f1": f"{trigger_metrics['f1']:.4f}",
        "entity_selection_micro_f1": f"{entity_prf['f1']:.4f}",
    }
    return {"summary": summary}


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Structured DSL Accuracy Report",
        "",
        "## 核心机器学习指标",
        "",
        f"- Sample Count: {summary['sample_count']}",
        f"- Exact Match: {summary['exact_match_rate']}",
        f"- Field Accuracy: {summary['field_accuracy']}",
        f"- Trigger Type F1: {summary['trigger_type_f1']}",
        f"- Entity Selection Micro-F1: {summary['entity_selection_micro_f1']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    result = evaluate_cases(load_eval_cases())
    report = render_report(result)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
