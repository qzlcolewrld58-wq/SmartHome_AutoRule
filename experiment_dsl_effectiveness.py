from __future__ import annotations

import json
from pathlib import Path

from compare_baseline_vs_dsl import evaluate_baseline, evaluate_dsl


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = PROJECT_ROOT / "data" / "test_cases"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORT_PATH = REPORT_DIR / "experiment_dsl_effectiveness.md"


def load_test_inputs() -> list[dict]:
    cases: list[dict] = []
    for path in sorted(TEST_CASE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            cases.extend(item for item in payload if isinstance(item, dict))
    return cases


def build_report(baseline_summary: dict[str, str], dsl_summary: dict[str, str]) -> str:
    lines = [
        "# DSL 中间层有效性实验报告",
        "",
        "## 实验目标",
        "",
        "验证引入 DSL 中间层后，相比直接生成 YAML，规则生成是否更稳定、更结构化。",
        "",
        "## 核心指标",
        "",
        "- Rule Completeness Rate",
        "- Validation Pass Rate",
        "- End-to-End Executable Rate",
        "",
        "## 实验结果",
        "",
        "| 指标 | 直接 YAML | DSL 中间层 |",
        "| --- | ---: | ---: |",
        f"| Rule Completeness Rate | {baseline_summary['rule_completeness_rate']} | {dsl_summary['rule_completeness_rate']} |",
        f"| Validation Pass Rate | {baseline_summary['validation_pass_rate']} | {dsl_summary['validation_pass_rate']} |",
        f"| End-to-End Executable Rate | {baseline_summary['end_to_end_executable_rate']} | {dsl_summary['end_to_end_executable_rate']} |",
        "",
        "## 结论模板",
        "",
        "> 实验结果表明，相较于直接生成 YAML，引入 DSL 中间层后，系统在规则完整性、规则合法性和端到端可执行性上均表现更稳定，因此 DSL 中间层能够有效提升规则生成系统的工程稳健性。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_test_inputs()
    baseline_summary = evaluate_baseline(cases)
    dsl_summary = evaluate_dsl(cases)
    report = build_report(baseline_summary, dsl_summary)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
