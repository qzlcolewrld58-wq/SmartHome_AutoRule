from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


class HomeAssistantYamlConverter:
    """Convert RuleDSL objects into Home Assistant style YAML."""

    def convert(self, rule: RuleDSL) -> str:
        automation = self.to_automation_dict(rule)
        return yaml.safe_dump(
            automation,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    def to_automation_dict(self, rule: RuleDSL) -> dict[str, Any]:
        return {
            "alias": rule.rule_name,
            "trigger": [self._convert_trigger(rule.trigger)],
            "condition": self._convert_conditions(rule.conditions),
            "action": self._convert_actions(rule.actions),
            "mode": rule.mode,
        }

    def _convert_trigger(self, trigger: TimeTrigger | StateChangeTrigger | EventTrigger) -> dict[str, Any]:
        if isinstance(trigger, TimeTrigger):
            return self._convert_time_trigger(trigger)
        if isinstance(trigger, StateChangeTrigger):
            return self._convert_state_change_trigger(trigger)
        if isinstance(trigger, EventTrigger):
            return self._convert_event_trigger(trigger)
        raise TypeError(f"Unsupported trigger type: {type(trigger)!r}")

    def _convert_time_trigger(self, trigger: TimeTrigger) -> dict[str, Any]:
        return {
            "platform": "time",
            "at": trigger.at,
        }

    def _convert_state_change_trigger(self, trigger: StateChangeTrigger) -> dict[str, Any]:
        result: dict[str, Any] = {
            "platform": "state",
            "entity_id": trigger.entity,
        }
        if trigger.from_state is not None:
            result["from"] = trigger.from_state
        if trigger.to_state is not None:
            result["to"] = trigger.to_state
        return result

    def _convert_event_trigger(self, trigger: EventTrigger) -> dict[str, Any]:
        result: dict[str, Any] = {
            "platform": "event",
            "event_type": trigger.event_type,
        }
        if trigger.event_data:
            result["event_data"] = trigger.event_data
        return result

    def _convert_conditions(
        self,
        conditions: list[StateCondition | TimeRangeCondition | WeekdayCondition],
    ) -> list[dict[str, Any]]:
        return [self._convert_condition(condition) for condition in conditions]

    def _convert_condition(
        self,
        condition: StateCondition | TimeRangeCondition | WeekdayCondition,
    ) -> dict[str, Any]:
        if isinstance(condition, StateCondition):
            return self._convert_state_condition(condition)
        if isinstance(condition, TimeRangeCondition):
            return self._convert_time_range_condition(condition)
        if isinstance(condition, WeekdayCondition):
            return self._convert_weekday_condition(condition)
        raise TypeError(f"Unsupported condition type: {type(condition)!r}")

    def _convert_state_condition(self, condition: StateCondition) -> dict[str, Any]:
        return {
            "condition": "state",
            "entity_id": condition.entity,
            "state": condition.expected_state,
        }

    def _convert_time_range_condition(self, condition: TimeRangeCondition) -> dict[str, Any]:
        return {
            "condition": "time",
            "after": condition.start,
            "before": condition.end,
        }

    def _convert_weekday_condition(self, condition: WeekdayCondition) -> dict[str, Any]:
        return {
            "condition": "time",
            "weekday": condition.days,
        }

    def _convert_actions(self, actions: list[ActionDSL]) -> list[dict[str, Any]]:
        return [self._convert_action(action) for action in actions]

    def _convert_action(self, action: ActionDSL) -> dict[str, Any]:
        result: dict[str, Any] = {
            "service": action.service,
            "target": {
                "entity_id": action.entity,
            },
        }
        if action.data:
            result["data"] = action.data
        return result


if __name__ == "__main__":
    from models.dsl_models import (
        ActionDSL,
        RuleDSL,
        StateChangeTrigger,
        TimeRangeCondition,
        WeekdayCondition,
    )

    sample_rule = RuleDSL(
        rule_name="玄关夜间有人时开灯",
        trigger=StateChangeTrigger(
            entity="sensor.entryway_motion",
            from_state="off",
            to_state="on",
        ),
        conditions=[
            TimeRangeCondition(start="18:00:00", end="23:59:59"),
            WeekdayCondition(days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"]),
        ],
        actions=[
            ActionDSL(
                service="light.turn_on",
                entity="light.entryway_light",
                data={"brightness": 180},
            )
        ],
        mode="restart",
    )

    converter = HomeAssistantYamlConverter()
    print(converter.convert(sample_rule))
