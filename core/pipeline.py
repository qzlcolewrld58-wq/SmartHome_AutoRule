from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.explainer import explain_rule
from core.metric_utils import (
    error_combo,
    parse_yaml_text,
)
from core.parser import ParserOutputError, parse_rule_text_with_meta
from core.repairer import DSLRepairer
from core.validator import DSLValidator
from core.visualizer import render_mermaid, render_text_tree
from core.yaml_converter import HomeAssistantYamlConverter
from models.device_models import load_default_registry
from models.dsl_models import RuleDSL


def process_rule(user_input: str, llm_client: Any) -> dict[str, Any]:
    """Run the end-to-end DSL experiment pipeline for one Chinese rule description."""

    registry = load_default_registry(PROJECT_ROOT)
    entity_list = registry.get_all_entity_ids()

    try:
        draft_payload, parser_telemetry = parse_rule_text_with_meta(user_input, entity_list, llm_client)
    except ParserOutputError as exc:
        validation = _build_validation_stub("parser_output_error", str(exc))
        mock_telemetry = dict(getattr(llm_client, "last_trace", {}) or {})
        return {
            "input_text": user_input,
            "draft_dsl": {},
            "repaired_dsl": {},
            "validation_before": validation,
            "repairs": [],
            "validation_after": validation,
            "yaml": "",
            "explanation": "",
            "text_tree": "",
            "mermaid_diagram": "",
            "telemetry": {
                "parser": exc.telemetry,
                "mock": mock_telemetry,
            },
            "metrics": {
                "end_to_end_executable": False,
            },
            "error": str(exc),
        }

    mock_telemetry = dict(getattr(llm_client, "last_trace", {}) or {})
    validator = DSLValidator(device_registry=registry)
    repairer = DSLRepairer(device_registry=registry)
    converter = HomeAssistantYamlConverter()

    validation_before = validator.validate_payload(draft_payload)
    repair_result = repairer.repair_payload(draft_payload)

    repaired_payload = repair_result.repaired_payload
    validation_after = validator.validate_payload(repaired_payload)

    repaired_rule = repair_result.repaired_rule
    if repaired_rule is None and validation_after.is_valid:
        repaired_rule = RuleDSL.model_validate(repaired_payload)

    yaml_text = ""
    explanation = ""
    text_tree = ""
    mermaid_diagram = ""
    yaml_parseable = False

    if repaired_rule is not None and validation_after.is_valid:
        yaml_text = converter.convert(repaired_rule)
        yaml_parseable, _ = parse_yaml_text(yaml_text)
        explanation = explain_rule(repaired_rule)
        text_tree = render_text_tree(repaired_rule)
        mermaid_diagram = render_mermaid(repaired_rule)
        _write_mermaid_report(mermaid_diagram)

    validation_before_dump = validation_before.model_dump()
    validation_after_dump = validation_after.model_dump()
    metrics = {
        "end_to_end_executable": bool(yaml_text) and yaml_parseable and validation_after.is_valid,
    }

    return {
        "input_text": user_input,
        "draft_dsl": draft_payload,
        "repaired_dsl": repaired_payload,
        "validation_before": validation_before_dump,
        "repairs": [log.model_dump() for log in repair_result.repair_logs],
        "validation_after": validation_after_dump,
        "yaml": yaml_text,
        "explanation": explanation,
        "text_tree": text_tree,
        "mermaid_diagram": mermaid_diagram,
        "telemetry": {
            "parser": parser_telemetry,
            "mock": mock_telemetry,
            "error_combo_before": error_combo(validation_before_dump),
            "error_combo_after": error_combo(validation_after_dump),
        },
        "metrics": metrics,
    }


def _build_validation_stub(error_type: str, message: str) -> dict[str, Any]:
    return {
        "is_valid": False,
        "errors": [{"type": error_type, "field": "parser", "message": message}],
        "warnings": [],
    }


def _write_mermaid_report(mermaid_diagram: str) -> None:
    report_dir = PROJECT_ROOT / "outputs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "rule_diagram.md"
    content = f"```mermaid\n{mermaid_diagram}\n```\n"
    report_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    from mock_llm_client import MockLLMClient

    sample_input = "玄关有人时开灯"
    result = process_rule(sample_input, MockLLMClient())
    print(json.dumps(result, ensure_ascii=False, indent=2))
