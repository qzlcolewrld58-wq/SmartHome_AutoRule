from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class BaseDSLModel(BaseModel):
    """Shared configuration for all DSL models."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TimeTrigger(BaseDSLModel):
    """Trigger a rule at a specific time."""

    type: Literal["time"] = "time"
    at: str = Field(
        default="07:00:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$",
        description="Time in HH:MM or HH:MM:SS format",
    )


class StateChangeTrigger(BaseDSLModel):
    """Trigger when a device state changes."""

    type: Literal["state_change"] = "state_change"
    entity: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$",
        description="Entity id such as sensor.living_room_temperature",
    )
    from_state: str | None = Field(
        default=None,
        min_length=1,
        description="Optional previous state",
    )
    to_state: str | None = Field(
        default=None,
        min_length=1,
        description="Optional target state",
    )


class EventTrigger(BaseDSLModel):
    """Trigger when a platform event occurs."""

    type: Literal["event"] = "event"
    event_type: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Event type name",
    )
    event_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional event payload filter",
    )


TriggerDSL = Annotated[
    Union[TimeTrigger, StateChangeTrigger, EventTrigger],
    Field(discriminator="type"),
]


class StateCondition(BaseDSLModel):
    """Condition based on a current entity state."""

    type: Literal["state"] = "state"
    entity: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$",
        description="Entity id",
    )
    expected_state: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Expected current state",
    )


class TimeRangeCondition(BaseDSLModel):
    """Condition restricted to a time range."""

    type: Literal["time_range"] = "time_range"
    start: str = Field(
        default="00:00:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$",
        description="Range start time",
    )
    end: str = Field(
        default="23:59:59",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$",
        description="Range end time",
    )


class WeekdayCondition(BaseDSLModel):
    """Condition restricted to specific weekdays."""

    type: Literal["weekday"] = "weekday"
    days: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(
        default_factory=list,
        min_length=1,
        description="Allowed weekdays",
    )


ConditionDSL = Annotated[
    Union[StateCondition, TimeRangeCondition, WeekdayCondition],
    Field(discriminator="type"),
]


class ActionDSL(BaseDSLModel):
    """Action to execute when the rule is triggered."""

    service: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$",
        description="Home Assistant style service, such as light.turn_on",
    )
    entity: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$",
        description="Target entity id",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional service data",
    )


class RuleDSL(BaseDSLModel):
    """First version of the automation DSL."""

    rule_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human readable rule name",
    )
    trigger: TriggerDSL = Field(..., description="Rule trigger")
    conditions: list[ConditionDSL] = Field(
        default_factory=list,
        description="Optional rule conditions",
    )
    actions: list[ActionDSL] = Field(
        ...,
        min_length=1,
        description="At least one action is required",
    )
    mode: Literal["single", "restart", "queued"] = Field(
        default="single",
        description="Execution mode",
    )


class ValidationIssue(BaseDSLModel):
    """Validation issue reported by later pipeline stages."""

    field: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: Literal["error", "warning"] = "error"


class ValidationResult(BaseDSLModel):
    """Validation result container."""

    is_valid: bool = False
    issues: list[ValidationIssue] = Field(default_factory=list)


class PipelineResult(BaseDSLModel):
    """Reserved pipeline result model for later stages."""

    source_text: str = Field(..., min_length=1)
    dsl: RuleDSL
    repaired_dsl: RuleDSL
    validation: ValidationResult
    yaml_text: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)


if __name__ == "__main__":
    sample_rule = RuleDSL(
        rule_name="工作日晚间开客厅灯",
        trigger=StateChangeTrigger(
            entity="sensor.entryway_motion",
            from_state="off",
            to_state="on",
        ),
        conditions=[
            TimeRangeCondition(start="18:00:00", end="23:00:00"),
            WeekdayCondition(days=["mon", "tue", "wed", "thu", "fri"]),
        ],
        actions=[
            ActionDSL(
                service="light.turn_on",
                entity="light.living_room_main",
                data={"brightness": 180},
            )
        ],
        mode="single",
    )
    print(sample_rule.model_dump_json(indent=2))
