from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.data_utils import extract_gold_rules
from models.device_models import DeviceRegistry, load_default_registry
from models.dsl_models import (
    EventTrigger,
    RuleDSL,
    StateChangeTrigger,
    StateCondition,
    TimeRangeCondition,
    TimeTrigger,
    WeekdayCondition,
)


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
ALLOWED_WEEKDAYS = {
    "mon",
    "tue",
    "wed",
    "thu",
    "fri",
    "sat",
    "sun",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
CONTROL_ACTION_OPPOSITES = {
    "turn_on": "turn_off",
    "turn_off": "turn_on",
    "open_cover": "close_cover",
    "close_cover": "open_cover",
    "lock": "unlock",
    "unlock": "lock",
}


class ValidationMessage(BaseModel):
    type: str = Field(..., min_length=1)
    field: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class RuleValidationResult(BaseModel):
    is_valid: bool = False
    errors: list[ValidationMessage] = Field(default_factory=list)
    warnings: list[ValidationMessage] = Field(default_factory=list)


class DSLValidator:
    """Validate RuleDSL schema and business constraints against the device registry."""

    def __init__(self, device_registry: DeviceRegistry | None = None) -> None:
        self.device_registry = device_registry or load_default_registry(PROJECT_ROOT)

    def validate_payload(self, payload: dict[str, Any]) -> RuleValidationResult:
        result = RuleValidationResult()

        try:
            rule = RuleDSL.model_validate(payload)
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"])
                result.errors.append(
                    ValidationMessage(
                        type="schema_error",
                        field=location or "rule",
                        message=error["msg"],
                    )
                )
            result.is_valid = False
            return result

        return self.validate_rule(rule)

    def validate_rule(self, rule: RuleDSL) -> RuleValidationResult:
        result = RuleValidationResult()

        self._validate_trigger(rule, result)
        self._validate_conditions(rule, result)
        self._validate_actions(rule, result)
        self._validate_action_conflicts(rule, result)

        result.is_valid = not result.errors
        return result

    def _validate_trigger(self, rule: RuleDSL, result: RuleValidationResult) -> None:
        trigger = rule.trigger

        if isinstance(trigger, TimeTrigger):
            if not getattr(trigger, "at", None):
                self._add_error(
                    result,
                    "missing_time_value",
                    "trigger.at",
                    "time 触发器缺少时间值。",
                )
            elif not self._is_valid_time(trigger.at):
                self._add_error(
                    result,
                    "invalid_time_value",
                    "trigger.at",
                    f"time 触发器时间格式不合法: {trigger.at}",
                )

        elif isinstance(trigger, StateChangeTrigger):
            if not self.device_registry.entity_exists(trigger.entity):
                self._add_error(
                    result,
                    "entity_not_found",
                    "trigger.entity",
                    f"触发器引用的实体不存在: {trigger.entity}",
                )

        elif isinstance(trigger, EventTrigger):
            entity_id = trigger.event_data.get("entity_id")
            if isinstance(entity_id, str) and entity_id and not self.device_registry.entity_exists(entity_id):
                self._add_warning(
                    result,
                    "event_entity_not_found",
                    "trigger.event_data.entity_id",
                    f"事件数据中的实体不存在: {entity_id}",
                )

    def _validate_conditions(self, rule: RuleDSL, result: RuleValidationResult) -> None:
        for index, condition in enumerate(rule.conditions):
            if isinstance(condition, StateCondition):
                if not self.device_registry.entity_exists(condition.entity):
                    self._add_error(
                        result,
                        "entity_not_found",
                        f"conditions[{index}].entity",
                        f"条件引用的实体不存在: {condition.entity}",
                    )

            elif isinstance(condition, TimeRangeCondition):
                if not condition.start:
                    self._add_error(
                        result,
                        "missing_time_range_start",
                        f"conditions[{index}].start",
                        "time_range condition 缺少 start。",
                    )
                elif not self._is_valid_time(condition.start):
                    self._add_error(
                        result,
                        "invalid_time_range_start",
                        f"conditions[{index}].start",
                        f"time_range condition 的 start 不合法: {condition.start}",
                    )

                if not condition.end:
                    self._add_error(
                        result,
                        "missing_time_range_end",
                        f"conditions[{index}].end",
                        "time_range condition 缺少 end。",
                    )
                elif not self._is_valid_time(condition.end):
                    self._add_error(
                        result,
                        "invalid_time_range_end",
                        f"conditions[{index}].end",
                        f"time_range condition 的 end 不合法: {condition.end}",
                    )

            elif isinstance(condition, WeekdayCondition):
                if not condition.days:
                    self._add_error(
                        result,
                        "missing_weekdays",
                        f"conditions[{index}].days",
                        "weekday condition 至少需要一个取值。",
                    )
                for day_index, day in enumerate(condition.days):
                    normalized_day = day.lower()
                    if normalized_day not in ALLOWED_WEEKDAYS:
                        self._add_error(
                            result,
                            "invalid_weekday",
                            f"conditions[{index}].days[{day_index}]",
                            f"weekday condition 的值不合法: {day}",
                        )

    def _validate_actions(self, rule: RuleDSL, result: RuleValidationResult) -> None:
        if not rule.actions:
            self._add_error(
                result,
                "empty_actions",
                "actions",
                "actions 不能为空。",
            )
            return

        for index, action in enumerate(rule.actions):
            device = self.device_registry.get_device(action.entity)
            field_prefix = f"actions[{index}]"

            if device is None:
                self._add_error(
                    result,
                    "entity_not_found",
                    f"{field_prefix}.entity",
                    f"动作引用的实体不存在: {action.entity}",
                )
                continue

            if action.service not in device.supported_services:
                self._add_error(
                    result,
                    "unsupported_service",
                    f"{field_prefix}.service",
                    f"实体 {action.entity} 不支持服务 {action.service}",
                )

            if device.type == "sensor":
                self._add_error(
                    result,
                    "sensor_not_controllable",
                    f"{field_prefix}.entity",
                    f"传感器实体不应执行控制动作: {action.entity}",
                )

    def _validate_action_conflicts(self, rule: RuleDSL, result: RuleValidationResult) -> None:
        services_by_entity: dict[str, set[str]] = {}
        reported_conflicts: set[tuple[str, str, str]] = set()

        for action in rule.actions:
            action_name = action.service.split(".")[-1]
            services_by_entity.setdefault(action.entity, set()).add(action_name)

        for entity_id, action_names in services_by_entity.items():
            for action_name in list(action_names):
                opposite = CONTROL_ACTION_OPPOSITES.get(action_name)
                if opposite and opposite in action_names:
                    conflict_key = tuple(sorted((entity_id, action_name, opposite)))
                    if conflict_key in reported_conflicts:
                        continue
                    reported_conflicts.add(conflict_key)
                    self._add_error(
                        result,
                        "conflicting_actions",
                        "actions",
                        f"同一规则中设备 {entity_id} 同时存在相反动作: {action_name} 和 {opposite}",
                    )

    @staticmethod
    def _is_valid_time(value: str) -> bool:
        return bool(TIME_PATTERN.fullmatch(value))

    @staticmethod
    def _add_error(
        result: RuleValidationResult,
        error_type: str,
        field: str,
        message: str,
    ) -> None:
        result.errors.append(
            ValidationMessage(
                type=error_type,
                field=field,
                message=message,
            )
        )

    @staticmethod
    def _add_warning(
        result: RuleValidationResult,
        warning_type: str,
        field: str,
        message: str,
    ) -> None:
        result.warnings.append(
            ValidationMessage(
                type=warning_type,
                field=field,
                message=message,
            )
        )


def validate_rule(rule: RuleDSL, device_registry: DeviceRegistry | None = None) -> RuleValidationResult:
    return DSLValidator(device_registry=device_registry).validate_rule(rule)


def validate_payload(
    payload: dict[str, Any],
    device_registry: DeviceRegistry | None = None,
) -> RuleValidationResult:
    return DSLValidator(device_registry=device_registry).validate_payload(payload)


if __name__ == "__main__":
    gold_path = PROJECT_ROOT / "data" / "gold_dsl.json"
    payloads = extract_gold_rules(gold_path)
    validator = DSLValidator()
    validation_result = validator.validate_payload(payloads[0])
    print(validation_result.model_dump_json(indent=2, ensure_ascii=False))
