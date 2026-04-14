from __future__ import annotations

import json
from pathlib import Path

from core.metric_utils import is_complete_dsl, rate
from core.pipeline import process_rule
from llm_client_factory import get_experiment_llm_client


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = PROJECT_ROOT / "data" / "test_cases"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
RESULT_PATH = REPORT_DIR / "batch_results.json"


def load_test_cases() -> list[dict]:
    cases: list[dict] = []
    for path in sorted(TEST_CASE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    case = dict(item)
                    case["_source_file"] = path.name
                    cases.append(case)
    return cases


def run_one_case(case: dict, llm_client: object) -> dict:
    result_record = {
        "input_text": case["input_text"],
        "category": case.get("category", "unknown"),
        "expected_difficulty": case.get("expected_difficulty", "unknown"),
        "source_file": case.get("_source_file", ""),
        "rule_complete": False,
        "validation_passed_before": False,
        "validation_passed_after": False,
        "end_to_end_executable": False,
        "error": None,
    }

    try:
        pipeline_result = process_rule(case["input_text"], llm_client)
        result_record["rule_complete"] = is_complete_dsl(pipeline_result.get("repaired_dsl", {}))
        result_record["validation_passed_before"] = bool(
            pipeline_result.get("validation_before", {}).get("is_valid", False)
        )
        result_record["validation_passed_after"] = bool(
            pipeline_result.get("validation_after", {}).get("is_valid", False)
        )
        result_record["end_to_end_executable"] = bool(
            pipeline_result.get("metrics", {}).get("end_to_end_executable", False)
        )
    except Exception as exc:
        result_record["error"] = str(exc)

    return result_record


def summarize(results: list[dict]) -> dict:
    total = len(results)
    pre = sum(1 for item in results if item["validation_passed_before"])
    post = sum(1 for item in results if item["validation_passed_after"])
    return {
        "total_samples": total,
        "rule_completeness_count": sum(1 for item in results if item["rule_complete"]),
        "validation_passed_before_count": pre,
        "validation_passed_after_count": post,
        "end_to_end_executable_count": sum(1 for item in results if item["end_to_end_executable"]),
        "repair_gain_rate": ((post - pre) / total) if total else 0.0,
    }


def print_summary(summary: dict) -> None:
    total = summary["total_samples"]
    print("Batch Experiment Summary")
    print(f"总样本数: {total}")
    print(f"规则完整率: {rate(summary['rule_completeness_count'], total)}")
    print(f"修复前校验通过率: {rate(summary['validation_passed_before_count'], total)}")
    print(f"修复后校验通过率: {rate(summary['validation_passed_after_count'], total)}")
    print(f"端到端可执行率: {rate(summary['end_to_end_executable_count'], total)}")
    print(f"自动修复增益: {summary['repair_gain_rate'] * 100:.2f}%")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    llm_client = get_experiment_llm_client()
    cases = load_test_cases()
    results = [run_one_case(case, llm_client) for case in cases]
    summary = summarize(results)

    payload = {"summary": summary, "results": results}
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print_summary(summary)
    print(f"结果文件: {RESULT_PATH}")


if __name__ == "__main__":
    main()
