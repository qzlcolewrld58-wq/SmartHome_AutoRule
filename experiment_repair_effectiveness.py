from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from core.data_utils import extract_gold_rules
from core.metric_utils import rate
from core.repairer import DSLRepairer
from core.validator import DSLValidator
from models.device_models import load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORT_PATH = REPORT_DIR / "experiment_repair_effectiveness.md"
GOLD_DSL_PATH = PROJECT_ROOT / "data" / "gold_dsl.json"


def load_gold_rules() -> list[dict[str, Any]]:
    return extract_gold_rules(GOLD_DSL_PATH)


def inject_error(rule: dict[str, Any], error_type: str, index: int) -> dict[str, Any]:
    payload = json.loads(json.dumps(rule, ensure_ascii=False))

    if error_type == "missing_mode":
        payload.pop("mode", None)
    elif error_type == "action_entity_typo":
        payload["actions"][0]["entity"] = payload["actions"][0]["entity"].replace("room", "rom", 1)
    elif error_type == "trigger_entity_typo" and payload["trigger"]["type"] == "state_change":
        payload["trigger"]["entity"] = payload["trigger"]["entity"].replace("motion", "motin", 1)
    elif error_type == "condition_entity_typo":
        if not payload["conditions"]:
            payload["conditions"] = [{"type": "state", "entity": "light.entryway_ligt", "expected_state": "off"}]
        else:
            for condition in payload["conditions"]:
                if condition.get("type") == "state":
                    condition["entity"] = condition["entity"].replace("room", "rom", 1)
                    break
            else:
                payload["conditions"].append({"type": "state", "entity": "light.entryway_ligt", "expected_state": "off"})
    elif error_type == "service_prefix_mismatch":
        payload["actions"][0]["service"] = "switch.turn_on"
    elif error_type == "conflicting_actions":
        action = payload["actions"][0]
        opposite_service = "light.turn_off" if action["service"].endswith("turn_on") else "light.turn_on"
        payload["actions"].append({"service": opposite_service, "entity": action["entity"], "data": {}})
    elif error_type == "invalid_weekday":
        payload.setdefault("conditions", []).append({"type": "weekday", "days": ["mon", "someday"]})
    elif error_type == "invalid_time":
        payload["trigger"] = {"type": "time", "at": "25:00:00"}

    payload["_sample_id"] = f"{error_type}_{index}"
    payload["_error_type"] = error_type
    return payload


def build_error_samples(base_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    error_types = [
        "missing_mode",
        "action_entity_typo",
        "trigger_entity_typo",
        "condition_entity_typo",
        "service_prefix_mismatch",
        "conflicting_actions",
        "invalid_weekday",
        "invalid_time",
    ]
    samples: list[dict[str, Any]] = []
    for index, rule in enumerate(base_rules):
        for error_type in error_types:
            samples.append(inject_error(rule, error_type, index))
    return samples


def run_experiment(samples: list[dict[str, Any]]) -> dict[str, Any]:
    registry = load_default_registry(PROJECT_ROOT)
    validator = DSLValidator(device_registry=registry)
    repairer = DSLRepairer(device_registry=registry)

    rows: list[dict[str, Any]] = []
    by_error: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for sample in samples:
        payload = {key: value for key, value in sample.items() if not key.startswith("_")}
        error_type = sample["_error_type"]
        before = validator.validate_payload(payload)
        repair_result = repairer.repair_payload(payload)
        after = validator.validate_payload(repair_result.repaired_payload)

        row = {
            "sample_id": sample["_sample_id"],
            "error_type": error_type,
            "before_valid": before.is_valid,
            "after_valid": after.is_valid,
            "repair_triggered": bool(repair_result.repair_logs),
            "repair_count": len(repair_result.repair_logs),
            "repaired_fields": [log.field for log in repair_result.repair_logs],
            "logic_conflict_resolved": (
                error_type == "conflicting_actions"
                and any(log.field == "actions" for log in repair_result.repair_logs)
                and after.is_valid
            ),
        }
        rows.append(row)
        by_error[error_type].append(row)

    total = len(rows)
    before_pass = sum(1 for row in rows if row["before_valid"])
    after_pass = sum(1 for row in rows if row["after_valid"])
    conflict_rows = [row for row in rows if row["error_type"] == "conflicting_actions"]
    conflict_fixed = sum(1 for row in conflict_rows if row["logic_conflict_resolved"])

    summary = {
        "total_samples": total,
        "before_pass_rate": rate(before_pass, total),
        "after_pass_rate": rate(after_pass, total),
        "repair_gain": f"{((after_pass - before_pass) / total) * 100:.2f}%" if total else "0.00%",
    }

    repair_success_by_error = {}
    for error_type, items in sorted(by_error.items()):
        total_error = len(items)
        fixed = sum(1 for item in items if not item["before_valid"] and item["after_valid"])
        repair_success_by_error[error_type] = {
            "total": total_error,
            "repair_success_rate": rate(fixed, total_error),
        }

    return {
        "rows": rows,
        "summary": summary,
        "repair_success_by_error": repair_success_by_error,
    }


def build_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    repair_success_by_error = result["repair_success_by_error"]

    lines = [
        "# 规则自校验与自动修复有效性实验报告",
        "",
        "## 实验目标",
        "",
        "验证校验与自动修复模块能否提升规则的最终可执行率。",
        "",
        "## 实验设置",
        "",
        f"- 注入错误样本数: {summary['total_samples']}",
        "- 样本来源: `data/gold_dsl.json` 的标准 DSL 样本",
        "- 注入错误类型: 缺失 mode、实体拼写错误、服务前缀错误、冲突动作、非法 weekday、非法时间等",
        "",
        "## 总体结果",
        "",
        f"- 修复前通过率: {summary['before_pass_rate']}",
        f"- 修复后通过率: {summary['after_pass_rate']}",
        f"- 自动修复增益: {summary['repair_gain']}",
        "",
        "## 不同错误类型的修复成功率",
        "",
        "| Error Type | Sample Count | Repair Success Rate |",
        "| --- | ---: | ---: |",
    ]

    for error_type, stat in repair_success_by_error.items():
        lines.append(
            f"| {error_type} | {stat['total']} | {stat['repair_success_rate']} |"
        )

    lines.extend(
        [
            "",
            "## 结论模板",
            "",
            "> 实验结果表明，规则自校验与自动修复模块能够有效提升最终规则的通过率，尤其对缺失默认字段、实体拼写错误、时间格式错误和逻辑冲突等可确定性错误具有明显修复效果。这说明“校验 + 局部修复”的组合能够显著增强规则生成系统的工程稳健性。",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    base_rules = load_gold_rules()
    samples = build_error_samples(base_rules)
    result = run_experiment(samples)
    report = build_report(result)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
