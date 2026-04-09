from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from core.metric_utils import rate


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
RESULT_PATH = REPORT_DIR / "batch_results.json"
TEXT_REPORT_PATH = REPORT_DIR / "report.txt"
MARKDOWN_REPORT_PATH = REPORT_DIR / "report.md"


def load_results() -> dict[str, Any]:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def build_group_stats(results: list[dict], group_key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in results:
        grouped[str(item.get(group_key, "unknown"))].append(item)

    stats: dict[str, dict[str, Any]] = {}
    for group, items in sorted(grouped.items()):
        total = len(items)
        pre = sum(1 for item in items if item.get("validation_passed_before"))
        post = sum(1 for item in items if item.get("validation_passed_after"))
        stats[group] = {
            "total": total,
            "rule_completeness_rate": rate(sum(1 for item in items if item.get("rule_complete")), total),
            "validation_pass_rate": rate(pre, total),
            "repair_after_pass_rate": rate(post, total),
            "repair_gain": f"{((post - pre) / total) * 100:.2f}%" if total else "0.00%",
            "end_to_end_executable_rate": rate(sum(1 for item in items if item.get("end_to_end_executable")), total),
        }
    return stats


def render_text_report(summary: dict[str, Any], category_stats: dict[str, Any], difficulty_stats: dict[str, Any]) -> str:
    total = int(summary.get("total_samples", 0))
    lines = [
        "Batch Analysis Report",
        "",
        f"总样本数: {total}",
        f"规则完整率: {rate(int(summary.get('rule_completeness_count', 0)), total)}",
        f"修复前校验通过率: {rate(int(summary.get('validation_passed_before_count', 0)), total)}",
        f"修复后校验通过率: {rate(int(summary.get('validation_passed_after_count', 0)), total)}",
        f"端到端可执行率: {rate(int(summary.get('end_to_end_executable_count', 0)), total)}",
        f"自动修复增益: {float(summary.get('repair_gain_rate', 0.0)) * 100:.2f}%",
        "",
        "按 category 统计:",
    ]
    for category, stat in category_stats.items():
        lines.append(
            f"- {category}: completeness={stat['rule_completeness_rate']}, "
            f"pre={stat['validation_pass_rate']}, post={stat['repair_after_pass_rate']}, "
            f"gain={stat['repair_gain']}, exec={stat['end_to_end_executable_rate']}"
        )

    lines.extend(["", "按 difficulty 统计:"])
    for difficulty, stat in difficulty_stats.items():
        lines.append(
            f"- {difficulty}: completeness={stat['rule_completeness_rate']}, "
            f"pre={stat['validation_pass_rate']}, post={stat['repair_after_pass_rate']}, "
            f"gain={stat['repair_gain']}, exec={stat['end_to_end_executable_rate']}"
        )

    return "\n".join(lines) + "\n"


def render_markdown_report(summary: dict[str, Any], category_stats: dict[str, Any], difficulty_stats: dict[str, Any]) -> str:
    total = int(summary.get("total_samples", 0))
    lines = [
        "# Batch Analysis Report",
        "",
        "## Overall Summary",
        "",
        f"- 总样本数: {total}",
        f"- Rule Completeness Rate: {rate(int(summary.get('rule_completeness_count', 0)), total)}",
        f"- Validation Pass Rate (Before Repair): {rate(int(summary.get('validation_passed_before_count', 0)), total)}",
        f"- Validation Pass Rate (After Repair): {rate(int(summary.get('validation_passed_after_count', 0)), total)}",
        f"- End-to-End Executable Rate: {rate(int(summary.get('end_to_end_executable_count', 0)), total)}",
        f"- Repair Gain: {float(summary.get('repair_gain_rate', 0.0)) * 100:.2f}%",
        "",
        "## Category Statistics",
        "",
        "| Category | Total | Rule Completeness Rate | Validation Pass Rate | Repair After Pass Rate | Repair Gain | End-to-End Executable Rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, stat in category_stats.items():
        lines.append(
            f"| {category} | {stat['total']} | {stat['rule_completeness_rate']} | {stat['validation_pass_rate']} | "
            f"{stat['repair_after_pass_rate']} | {stat['repair_gain']} | {stat['end_to_end_executable_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Difficulty Statistics",
            "",
            "| Difficulty | Total | Rule Completeness Rate | Validation Pass Rate | Repair After Pass Rate | Repair Gain | End-to-End Executable Rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for difficulty, stat in difficulty_stats.items():
        lines.append(
            f"| {difficulty} | {stat['total']} | {stat['rule_completeness_rate']} | {stat['validation_pass_rate']} | "
            f"{stat['repair_after_pass_rate']} | {stat['repair_gain']} | {stat['end_to_end_executable_rate']} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    payload = load_results()
    summary = payload.get("summary", {})
    results = payload.get("results", [])
    category_stats = build_group_stats(results, "category")
    difficulty_stats = build_group_stats(results, "expected_difficulty")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_REPORT_PATH.write_text(render_text_report(summary, category_stats, difficulty_stats), encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(render_markdown_report(summary, category_stats, difficulty_stats), encoding="utf-8")

    print(f"文本报告: {TEXT_REPORT_PATH}")
    print(f"Markdown 报告: {MARKDOWN_REPORT_PATH}")


if __name__ == "__main__":
    main()
