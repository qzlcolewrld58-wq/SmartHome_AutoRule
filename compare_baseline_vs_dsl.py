from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from baseline_direct_yaml import BaselineDirectYamlGenerator
from core.metric_utils import is_complete_yaml, parse_yaml_text, rate
from core.pipeline import process_rule
from mock_llm_client import MockLLMClient
from models.device_models import load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = PROJECT_ROOT / "data" / "test_cases"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORT_PATH = REPORT_DIR / "comparison_report.md"
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
VALID_WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
CONFLICT_PAIRS = {
    ("turn_on", "turn_off"),
    ("turn_off", "turn_on"),
    ("open_cover", "close_cover"),
    ("close_cover", "open_cover"),
}


def load_test_inputs() -> list[dict]:
    cases: list[dict] = []
    for path in sorted(TEST_CASE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            cases.extend(item for item in payload if isinstance(item, dict))
    return cases


def evaluate_baseline(cases: list[dict]) -> dict[str, str]:
    generator = BaselineDirectYamlGenerator()
    registry = load_default_registry(PROJECT_ROOT)
    total = len(cases)
    complete = valid = executable = 0

    for case in cases:
        try:
            yaml_text = generator.generate(case["input_text"])
            parseable, parsed = parse_yaml_text(yaml_text)
            if parseable and isinstance(parsed, dict):
                if is_complete_yaml(parsed):
                    complete += 1
                if validate_rule_yaml(parsed, registry):
                    valid += 1
                    executable += 1
        except Exception:
            pass

    return {
        "sample_count": str(total),
        "rule_completeness_rate": rate(complete, total),
        "validation_pass_rate": rate(valid, total),
        "end_to_end_executable_rate": rate(executable, total),
    }


def evaluate_dsl(cases: list[dict]) -> dict[str, str]:
    client = MockLLMClient()
    total = len(cases)
    complete = valid = executable = 0

    for case in cases:
        result = process_rule(case["input_text"], client)
        if result.get("repaired_dsl"):
            from core.metric_utils import is_complete_dsl

            if is_complete_dsl(result["repaired_dsl"]):
                complete += 1
        if result.get("validation_after", {}).get("is_valid", False):
            valid += 1
        if result.get("metrics", {}).get("end_to_end_executable", False):
            executable += 1

    return {
        "sample_count": str(total),
        "rule_completeness_rate": rate(complete, total),
        "validation_pass_rate": rate(valid, total),
        "end_to_end_executable_rate": rate(executable, total),
    }


def validate_rule_yaml(parsed: dict[str, Any], registry: Any) -> bool:
    if not is_complete_yaml(parsed):
        return False

    trigger = parsed["trigger"][0]
    if not isinstance(trigger, dict):
        return False

    platform = trigger.get("platform")
    if platform == "time":
        at = trigger.get("at")
        if not isinstance(at, str) or not TIME_PATTERN.fullmatch(at):
            return False
    elif platform == "state":
        entity_id = trigger.get("entity_id")
        if not isinstance(entity_id, str) or not registry.entity_exists(entity_id):
            return False
    elif platform == "event":
        if not isinstance(trigger.get("event_type"), str):
            return False
    else:
        return False

    for condition in parsed.get("condition", []):
        if not isinstance(condition, dict):
            return False
        if condition.get("condition") == "state":
            entity_id = condition.get("entity_id")
            if not isinstance(entity_id, str) or not registry.entity_exists(entity_id):
                return False
        if condition.get("condition") == "time":
            weekdays = condition.get("weekday")
            if weekdays is not None:
                if not isinstance(weekdays, list) or any(day not in VALID_WEEKDAYS for day in weekdays):
                    return False
            for key in ("after", "before"):
                value = condition.get(key)
                if value is not None and (not isinstance(value, str) or not TIME_PATTERN.fullmatch(value)):
                    return False

    services_by_entity: dict[str, set[str]] = {}
    for action in parsed["action"]:
        if not isinstance(action, dict):
            return False
        service = action.get("service")
        target = action.get("target")
        entity_id = target.get("entity_id") if isinstance(target, dict) else None
        if not isinstance(service, str) or not isinstance(entity_id, str):
            return False
        if not registry.entity_exists(entity_id):
            return False
        if service not in registry.get_supported_services(entity_id):
            return False
        services_by_entity.setdefault(entity_id, set()).add(service.split(".")[-1])

    for entity_id, service_names in services_by_entity.items():
        for left, right in CONFLICT_PAIRS:
            if left in service_names and right in service_names:
                return False
    return True


def render_markdown_report(baseline_summary: dict[str, str], dsl_summary: dict[str, str]) -> str:
    lines = [
        "# Baseline vs DSL Comparison",
        "",
        "## Methods",
        "",
        "- 方案 A: 直接从中文生成 YAML",
        "- 方案 B: 先生成 DSL，再转换为 YAML",
        "",
        "## Comparison Table",
        "",
        "| Metric | Direct YAML Baseline | DSL Middle Layer |",
        "| --- | ---: | ---: |",
        f"| Sample Count | {baseline_summary['sample_count']} | {dsl_summary['sample_count']} |",
        f"| Rule Completeness Rate | {baseline_summary['rule_completeness_rate']} | {dsl_summary['rule_completeness_rate']} |",
        f"| Validation Pass Rate | {baseline_summary['validation_pass_rate']} | {dsl_summary['validation_pass_rate']} |",
        f"| End-to-End Executable Rate | {baseline_summary['end_to_end_executable_rate']} | {dsl_summary['end_to_end_executable_rate']} |",
        "",
        "## Conclusion",
        "",
        "These three metrics are the main DSL-before-vs-after comparison metrics used in the paper draft.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_test_inputs()
    baseline_summary = evaluate_baseline(cases)
    dsl_summary = evaluate_dsl(cases)
    report = render_markdown_report(baseline_summary, dsl_summary)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
