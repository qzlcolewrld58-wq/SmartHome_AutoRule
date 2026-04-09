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


class RuleExplainer:
    """Convert RuleDSL into a concise Chinese explanation."""

    WEEKDAY_TEXT = {
        "mon": "周一",
        "tue": "周二",
        "wed": "周三",
        "thu": "周四",
        "fri": "周五",
        "sat": "周六",
        "sun": "周日",
    }

    MODE_TEXT = {
        "single": "单次执行模式",
        "restart": "重启模式",
        "queued": "排队模式",
    }

    def explain_rule(self, rule: RuleDSL) -> str:
        trigger_text = self._explain_trigger(rule)
        condition_text = self._explain_conditions(rule)
        action_text = self._explain_actions(rule.actions)
        mode_text = self.MODE_TEXT.get(rule.mode, rule.mode)

        return (
            f"规则“{rule.rule_name}”："
            f"{trigger_text}；"
            f"{condition_text}；"
            f"{action_text}；"
            f"执行方式为{mode_text}。"
        )

    def _explain_trigger(self, rule: RuleDSL) -> str:
        trigger = rule.trigger
        if isinstance(trigger, TimeTrigger):
            return f"在每天 {trigger.at} 触发"
        if isinstance(trigger, StateChangeTrigger):
            parts: list[str] = [f"当 {trigger.entity} 状态变化时触发"]
            if trigger.from_state is not None:
                parts.append(f"原状态为 {trigger.from_state}")
            if trigger.to_state is not None:
                parts.append(f"目标状态为 {trigger.to_state}")
            return "，".join(parts)
        if isinstance(trigger, EventTrigger):
            if trigger.event_data:
                payload = json.dumps(trigger.event_data, ensure_ascii=False)
                return f"当事件 {trigger.event_type} 发生且事件数据满足 {payload} 时触发"
            return f"当事件 {trigger.event_type} 发生时触发"
        return "触发方式未知"

    def _explain_conditions(self, rule: RuleDSL) -> str:
        if not rule.conditions:
            return "无额外条件"

        condition_texts: list[str] = []
        for condition in rule.conditions:
            if isinstance(condition, StateCondition):
                condition_texts.append(
                    f"{condition.entity} 当前状态为 {condition.expected_state}"
                )
            elif isinstance(condition, TimeRangeCondition):
                condition_texts.append(
                    f"时间处于 {condition.start} 到 {condition.end} 之间"
                )
            elif isinstance(condition, WeekdayCondition):
                days = [self.WEEKDAY_TEXT.get(day, day) for day in condition.days]
                condition_texts.append(f"日期属于 {'、'.join(days)}")

        return f"条件为：{'；'.join(condition_texts)}"

    def _explain_actions(self, actions: list[ActionDSL]) -> str:
        action_texts = [self._explain_action(action) for action in actions]
        return f"执行动作：{'；'.join(action_texts)}"

    def _explain_action(self, action: ActionDSL) -> str:
        if action.data:
            payload = json.dumps(action.data, ensure_ascii=False)
            return f"调用 {action.service} 操作 {action.entity}，参数为 {payload}"
        return f"调用 {action.service} 操作 {action.entity}"


def explain_rule(rule: RuleDSL) -> str:
    """Convenience function for one-off explanation generation."""

    return RuleExplainer().explain_rule(rule)


if __name__ == "__main__":
    gold_path = PROJECT_ROOT / "data" / "gold_dsl.json"
    rules = extract_gold_rules(gold_path)
    first_rule = RuleDSL.model_validate(rules[0])
    print(explain_rule(first_rule))
