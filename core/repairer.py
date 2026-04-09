from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from rapidfuzz import process

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.device_models import DeviceRegistry, load_default_registry
from models.dsl_models import RuleDSL


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
VALID_WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
OPPOSITE_ACTIONS = {
    "turn_on": "turn_off",
    "turn_off": "turn_on",
    "open_cover": "close_cover",
    "close_cover": "open_cover",
    "lock": "unlock",
    "unlock": "lock",
    "start": "stop",
    "stop": "start",
}


class RepairLogEntry(BaseModel):
    field: str = Field(..., min_length=1)
    original: Any = None
    fixed: Any = None
    reason: str = Field(..., min_length=1)


class RepairResult(BaseModel):
    repaired_payload: dict[str, Any]
    repaired_rule: RuleDSL | None = None
    repair_logs: list[RepairLogEntry] = Field(default_factory=list)


class DSLRepairer:
    def __init__(self, device_registry: DeviceRegistry | None = None, score_cutoff: int = 75) -> None:
        self.device_registry = device_registry or load_default_registry(PROJECT_ROOT)
        self.score_cutoff = score_cutoff
        self._entity_ids = self.device_registry.get_all_entity_ids()

    def repair_payload(self, payload: dict[str, Any]) -> RepairResult:
        repaired_payload = json.loads(json.dumps(payload, ensure_ascii=False))
        repair_logs: list[RepairLogEntry] = []

        self._repair_mode(repaired_payload, repair_logs)
        self._repair_trigger_entity(repaired_payload, repair_logs)
        self._repair_trigger_time(repaired_payload, repair_logs)
        self._repair_conditions(repaired_payload, repair_logs)
        self._repair_action_entities(repaired_payload, repair_logs)
        self._repair_sensor_actions(repaired_payload, repair_logs)
        self._repair_service_prefix_mismatch(repaired_payload, repair_logs)
        self._repair_conflicting_actions(repaired_payload, repair_logs)

        repaired_rule: RuleDSL | None = None
        try:
            repaired_rule = RuleDSL.model_validate(repaired_payload)
        except Exception:
            repaired_rule = None

        return RepairResult(
            repaired_payload=repaired_payload,
            repaired_rule=repaired_rule,
            repair_logs=repair_logs,
        )

    def repair_rule(self, rule: RuleDSL) -> RepairResult:
        return self.repair_payload(rule.model_dump())

    def _repair_mode(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        if "mode" not in payload or payload.get("mode") in (None, ""):
            payload["mode"] = "single"
            repair_logs.append(
                RepairLogEntry(
                    field="mode",
                    original=None,
                    fixed="single",
                    reason="mode 缺失，自动补全为默认值 single。",
                )
            )

    def _repair_trigger_entity(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        trigger = payload.get("trigger")
        if not isinstance(trigger, dict) or trigger.get("type") != "state_change":
            return
        entity = trigger.get("entity")
        fixed = self._match_entity(entity)
        if fixed and fixed != entity:
            trigger["entity"] = fixed
            repair_logs.append(
                RepairLogEntry(
                    field="trigger.entity",
                    original=entity,
                    fixed=fixed,
                    reason="触发器实体不存在，已使用近似匹配自动修复。",
                )
            )

    def _repair_trigger_time(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        trigger = payload.get("trigger")
        if not isinstance(trigger, dict) or trigger.get("type") != "time":
            return
        original = trigger.get("at")
        fixed = self._normalize_time(original, "20:00:00")
        if fixed != original:
            trigger["at"] = fixed
            repair_logs.append(
                RepairLogEntry(
                    field="trigger.at",
                    original=original,
                    fixed=fixed,
                    reason="time 触发器时间不合法，已自动规范化。",
                )
            )

    def _repair_conditions(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        conditions = payload.get("conditions")
        if not isinstance(conditions, list):
            return
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                continue
            if condition.get("type") == "state":
                original = condition.get("entity")
                fixed = self._match_entity(original)
                if fixed and fixed != original:
                    condition["entity"] = fixed
                    repair_logs.append(
                        RepairLogEntry(
                            field=f"conditions[{index}].entity",
                            original=original,
                            fixed=fixed,
                            reason="条件实体不存在，已使用近似匹配自动修复。",
                        )
                    )
            elif condition.get("type") == "weekday":
                original = condition.get("days")
                if isinstance(original, list):
                    fixed = [x.lower() for x in original if isinstance(x, str) and x.lower() in VALID_WEEKDAYS]
                    if not fixed:
                        fixed = ["mon", "tue", "wed", "thu", "fri"]
                    if fixed != original:
                        condition["days"] = fixed
                        repair_logs.append(
                            RepairLogEntry(
                                field=f"conditions[{index}].days",
                                original=original,
                                fixed=fixed,
                                reason="weekday condition 含有非法取值，已自动修正。",
                            )
                        )
            elif condition.get("type") == "time_range":
                for key, default in (("start", "00:00:00"), ("end", "23:59:59")):
                    original = condition.get(key)
                    fixed = self._normalize_time(original, default)
                    if fixed != original:
                        condition[key] = fixed
                        repair_logs.append(
                            RepairLogEntry(
                                field=f"conditions[{index}].{key}",
                                original=original,
                                fixed=fixed,
                                reason="time_range 条件时间不合法，已自动规范化。",
                            )
                        )

    def _repair_action_entities(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        actions = payload.get("actions")
        if not isinstance(actions, list):
            return
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            original = action.get("entity")
            fixed = self._match_entity(original)
            if fixed and fixed != original:
                action["entity"] = fixed
                repair_logs.append(
                    RepairLogEntry(
                        field=f"actions[{index}].entity",
                        original=original,
                        fixed=fixed,
                        reason="动作实体不存在，已使用近似匹配自动修复。",
                    )
                )

    def _repair_sensor_actions(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        actions = payload.get("actions")
        if not isinstance(actions, list):
            return
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            entity_id = action.get("entity")
            service = action.get("service")
            if not isinstance(entity_id, str) or not isinstance(service, str):
                continue
            device = self.device_registry.get_device(entity_id)
            if device is None or device.type != "sensor":
                continue
            replacement = self._find_room_device_for_service(device.room, service.split(".")[-1])
            if replacement is None:
                continue
            original = {"service": service, "entity": entity_id}
            action["service"] = replacement["service"]
            action["entity"] = replacement["entity_id"]
            repair_logs.append(
                RepairLogEntry(
                    field=f"actions[{index}]",
                    original=original,
                    fixed=replacement,
                    reason="动作错误地作用于传感器，已替换为同房间可控设备。",
                )
            )

    def _repair_service_prefix_mismatch(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        actions = payload.get("actions")
        if not isinstance(actions, list):
            return
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            entity_id = action.get("entity")
            service = action.get("service")
            if not isinstance(entity_id, str) or not isinstance(service, str):
                continue
            device = self.device_registry.get_device(entity_id)
            if device is None or not device.supported_services or service in device.supported_services:
                continue
            fixed = self._best_service(service, device.supported_services)
            if fixed != service:
                action["service"] = fixed
                repair_logs.append(
                    RepairLogEntry(
                        field=f"actions[{index}].service",
                        original=service,
                        fixed=fixed,
                        reason="service 与实体类型不匹配，已自动替换为支持的服务。",
                    )
                )

    def _repair_conflicting_actions(self, payload: dict[str, Any], repair_logs: list[RepairLogEntry]) -> None:
        actions = payload.get("actions")
        if not isinstance(actions, list) or len(actions) < 2:
            return
        original = json.loads(json.dumps(actions, ensure_ascii=False))
        kept: list[dict[str, Any]] = []
        seen: dict[str, set[str]] = {}
        changed = False
        for action in actions:
            if not isinstance(action, dict):
                kept.append(action)
                continue
            entity = action.get("entity")
            service = action.get("service")
            if not isinstance(entity, str) or not isinstance(service, str):
                kept.append(action)
                continue
            suffix = service.split(".")[-1]
            prev = seen.setdefault(entity, set())
            if OPPOSITE_ACTIONS.get(suffix) in prev:
                changed = True
                continue
            prev.add(suffix)
            kept.append(action)
        if changed:
            payload["actions"] = kept
            repair_logs.append(
                RepairLogEntry(
                    field="actions",
                    original=original,
                    fixed=kept,
                    reason="检测到同一设备相反动作，已保留首个动作并移除冲突动作。",
                )
            )

    def _match_entity(self, entity_id: Any) -> str | None:
        if not isinstance(entity_id, str) or not entity_id:
            return None
        if self.device_registry.entity_exists(entity_id):
            return entity_id
        match = process.extractOne(entity_id, self._entity_ids, score_cutoff=self.score_cutoff)
        return match[0] if match else None

    def _best_service(self, service: str, supported: list[str]) -> str:
        suffix = service.split(".")[-1] if "." in service else service
        mapped = {x.split(".")[-1]: x for x in supported}
        if suffix in mapped:
            return mapped[suffix]
        semantic = {
            "turn_on": ["turn_on", "open_cover", "unlock", "start"],
            "turn_off": ["turn_off", "close_cover", "lock", "stop"],
            "open_cover": ["open_cover", "turn_on"],
            "close_cover": ["close_cover", "turn_off"],
            "lock": ["lock", "turn_off"],
            "unlock": ["unlock", "turn_on"],
            "start": ["start", "turn_on"],
            "stop": ["stop", "turn_off"],
            "set_temperature": ["set_temperature", "set_hvac_mode"],
            "set_hvac_mode": ["set_hvac_mode", "set_temperature"],
            "set_humidity": ["set_humidity", "turn_on"],
        }
        for candidate in semantic.get(suffix, []):
            if candidate in mapped:
                return mapped[candidate]
        return supported[0]

    def _find_room_device_for_service(self, room: str, action_suffix: str) -> dict[str, str] | None:
        preferred = {
            "turn_on": ["light.turn_on", "switch.turn_on", "fan.turn_on", "climate.turn_on", "humidifier.turn_on"],
            "turn_off": ["light.turn_off", "switch.turn_off", "fan.turn_off", "climate.turn_off", "humidifier.turn_off"],
            "open_cover": ["cover.open_cover"],
            "close_cover": ["cover.close_cover"],
        }.get(action_suffix, ["light.turn_on", "switch.turn_on"])
        room_devices = [d for d in self.device_registry.devices if d.room == room]
        for service in preferred:
            for device in room_devices:
                if service in device.supported_services:
                    return {"entity_id": device.entity_id, "service": service}
        return None

    def _normalize_time(self, value: Any, default: str) -> str:
        if not isinstance(value, str) or not value:
            return default
        if TIME_PATTERN.fullmatch(value):
            return f"{value}:00" if len(value) == 5 else value
        m = re.search(r"(\d{1,2})[:：点](\d{1,2})?", value)
        if m:
            hour = min(int(m.group(1)), 23)
            minute = min(int(m.group(2) or 0), 59)
            return f"{hour:02d}:{minute:02d}:00"
        m2 = re.search(r"(\d{1,2})", value)
        if m2:
            return f"{min(int(m2.group(1)), 23):02d}:00:00"
        return default
