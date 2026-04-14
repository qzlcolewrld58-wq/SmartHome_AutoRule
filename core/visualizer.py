from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data_utils import extract_gold_rules
from models.dsl_models import (
    ActionDSL,
    EventTrigger,
    RuleDSL,
    StateChangeTrigger,
    StateCondition,
    TimeRangeCondition,
    TimeTrigger,
    WeekdayCondition,
)


def render_text_tree(rule: RuleDSL) -> str:
    lines: list[str] = [
        f"Rule: {rule.rule_name}",
        f"Mode: {rule.mode}",
        "Trigger:",
        f"  { _render_trigger_text(rule) }",
        "Conditions:",
    ]

    if rule.conditions:
        for index, condition in enumerate(rule.conditions, start=1):
            lines.append(f"  {index}. {_render_condition_text(condition)}")
    else:
        lines.append("  (none)")

    lines.append("Actions:")
    for index, action in enumerate(rule.actions, start=1):
        lines.append(f"  {index}. {_render_action_text(action)}")

    return "\n".join(lines)


def render_mermaid(rule: RuleDSL) -> str:
    lines: list[str] = [
        "flowchart TB",
        f'    RULE["Rule: {_escape_mermaid(rule.rule_name)}"]',
        f'    TRIGGER["Trigger: {_escape_mermaid(_render_trigger_text(rule))}"]',
        '    CONDITIONS["Conditions"]',
        '    ACTIONS["Actions"]',
        f'    MODE["Mode: {_escape_mermaid(rule.mode)}"]',
        "    RULE --> TRIGGER",
        "    RULE --> CONDITIONS",
        "    RULE --> ACTIONS",
        "    RULE --> MODE",
    ]

    if rule.conditions:
        for index, condition in enumerate(rule.conditions, start=1):
            node_name = f"C{index}"
            lines.append(
                f'    {node_name}["{index}. {_escape_mermaid(_render_condition_text(condition))}"]'
            )
            lines.append(f"    CONDITIONS --> {node_name}")
    else:
        lines.append('    C0["No conditions"]')
        lines.append("    CONDITIONS --> C0")

    for index, action in enumerate(rule.actions, start=1):
        node_name = f"A{index}"
        lines.append(
            f'    {node_name}["{index}. {_escape_mermaid(_render_action_text(action))}"]'
        )
        lines.append(f"    ACTIONS --> {node_name}")

    return "\n".join(lines)


def _render_trigger_text(rule: RuleDSL) -> str:
    trigger = rule.trigger
    if isinstance(trigger, TimeTrigger):
        return f"time at {trigger.at}"
    if isinstance(trigger, StateChangeTrigger):
        parts = [f"state_change {trigger.entity}"]
        if trigger.from_state is not None:
            parts.append(f"from={trigger.from_state}")
        if trigger.to_state is not None:
            parts.append(f"to={trigger.to_state}")
        return ", ".join(parts)
    if isinstance(trigger, EventTrigger):
        if trigger.event_data:
            return f"event {trigger.event_type}, data={json.dumps(trigger.event_data, ensure_ascii=False)}"
        return f"event {trigger.event_type}"
    return "unknown trigger"


def _render_condition_text(
    condition: StateCondition | TimeRangeCondition | WeekdayCondition,
) -> str:
    if isinstance(condition, StateCondition):
        return f"state {condition.entity} == {condition.expected_state}"
    if isinstance(condition, TimeRangeCondition):
        return f"time_range {condition.start} -> {condition.end}"
    if isinstance(condition, WeekdayCondition):
        return f"weekday {', '.join(condition.days)}"
    return "unknown condition"


def _render_action_text(action: ActionDSL) -> str:
    if action.data:
        return f"{action.service} -> {action.entity} with {json.dumps(action.data, ensure_ascii=False)}"
    return f"{action.service} -> {action.entity}"


def _escape_mermaid(text: str) -> str:
    return text.replace('"', "'")


if __name__ == "__main__":
    gold_path = PROJECT_ROOT / "data" / "gold_dsl.json"
    payloads = extract_gold_rules(gold_path)
    sample_rule = RuleDSL.model_validate(payloads[0])
    print(render_text_tree(sample_rule))
    print()
    print(render_mermaid(sample_rule))
