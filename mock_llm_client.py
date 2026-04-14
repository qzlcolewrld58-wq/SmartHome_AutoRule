from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from models.device_models import DeviceRegistry, load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent

ROOM_KEYWORDS = [
    ("master bathroom", "master_bathroom"),
    ("guest bathroom", "guest_bathroom"),
    ("master bedroom", "master_bedroom"),
    ("guest bedroom", "guest_bedroom"),
    ("living room", "living_room"),
    ("dining room", "dining_room"),
    ("study room", "study"),
    ("storage room", "storage_room"),
    ("store room", "storage_room"),
    ("laundry room", "laundry_room"),
    ("kids room", "kids_room"),
    ("children room", "kids_room"),
    ("entryway", "entryway"),
    ("corridor", "hallway"),
    ("hallway", "hallway"),
    ("bathroom", "bathroom"),
    ("bedroom", "bedroom"),
    ("kitchen", "kitchen"),
    ("balcony", "balcony"),
    ("closet", "closet"),
    ("garage", "garage"),
    ("garden", "garden"),
    ("basement", "basement"),
    ("foyer", "entryway"),
    ("客厅", "living_room"),
    ("主卧", "master_bedroom"),
    ("次卧", "guest_bedroom"),
    ("卧室", "bedroom"),
    ("儿童房", "kids_room"),
    ("书房", "study"),
    ("厨房", "kitchen"),
    ("餐厅", "dining_room"),
    ("卫生间", "bathroom"),
    ("主卫", "master_bathroom"),
    ("次卫", "guest_bathroom"),
    ("阳台", "balcony"),
    ("玄关", "entryway"),
    ("走廊", "hallway"),
    ("储物间", "storage_room"),
    ("衣帽间", "closet"),
    ("洗衣房", "laundry_room"),
    ("车库", "garage"),
    ("地下室", "basement"),
    ("花园", "garden"),
]

ROOM_FALLBACKS = [
    ("回家", "entryway"),
    ("进门", "entryway"),
    ("出门", "entryway"),
    ("come home", "entryway"),
    ("arrive home", "entryway"),
    ("leave home", "entryway"),
    ("sleep", "bedroom"),
    ("洗澡", "bathroom"),
    ("shower", "bathroom"),
    ("cook", "kitchen"),
]

DEVICE_HINTS = [
    ("air conditioner", "climate", "ac"),
    ("heating system", "climate", "ac"),
    ("heater", "climate", "ac"),
    ("thermostat", "climate", "thermostat"),
    ("dehumidifier", "dehumidifier", "dehumidifier"),
    ("humidifier", "humidifier", "humidifier"),
    ("air purifier", "switch", "purifier_power"),
    ("purifier", "switch", "purifier_power"),
    ("aromatherapy diffuser", "switch", "socket"),
    ("aromatherapy device", "switch", "socket"),
    ("aromatherapy", "switch", "socket"),
    ("water heater", "switch", "water_heater"),
    ("coffee machine", "switch", "coffee_machine"),
    ("rice cooker", "switch", "rice_cooker"),
    ("kettle", "switch", "kettle"),
    ("washing machine", "switch", "washer_power"),
    ("dryer", "switch", "dryer_power"),
    ("door lock", "lock", "door_lock"),
    ("smart lock", "lock", "smart_lock"),
    ("robot vacuum", "vacuum", "robot_vacuum"),
    ("vacuum", "vacuum", "robot_vacuum"),
    ("ceiling fan", "fan", "ceiling_fan"),
    ("standing fan", "fan", "standing_fan"),
    ("exhaust fan", "fan", "exhaust_fan"),
    ("fan", "fan", "standing_fan"),
    ("speaker", "media_player", "speaker"),
    ("projector", "media_player", "projector"),
    ("tv", "media_player", "tv"),
    ("television", "media_player", "tv"),
    ("doorbell camera", "camera", "doorbell_cam"),
    ("garage camera", "camera", "garage_cam"),
    ("outdoor camera", "camera", "outdoor_cam"),
    ("indoor camera", "camera", "indoor_cam"),
    ("camera", "camera", "indoor_cam"),
    ("motion sensor", "sensor", "motion"),
    ("temperature sensor", "sensor", "temperature"),
    ("humidity sensor", "sensor", "humidity"),
    ("door sensor", "sensor", "door"),
    ("window sensor", "sensor", "window"),
    ("smoke sensor", "sensor", "smoke"),
    ("co2 sensor", "sensor", "co2"),
    ("leak sensor", "sensor", "leak"),
    ("blind", "cover", "blind"),
    ("blinds", "cover", "blind"),
    ("shade", "cover", "shade"),
    ("curtain", "cover", "curtain"),
    ("curtains", "cover", "curtain"),
    ("bedside light", "light", "bedside_left"),
    ("desk lamp", "light", "desk_lamp"),
    ("floor lamp", "light", "floor_lamp"),
    ("night light", "light", "night_light"),
    ("light strip", "light", "strip"),
    ("ceiling light", "light", "ceiling"),
    ("wall light", "light", "wall"),
    ("light", "light", "main"),
    ("主灯", "light", "main"),
    ("台灯", "light", "lamp"),
    ("吊顶灯", "light", "ceiling"),
    ("壁灯", "light", "wall"),
    ("灯带", "light", "strip"),
    ("夜灯", "light", "night_light"),
    ("落地灯", "light", "floor_lamp"),
    ("书桌灯", "light", "desk_lamp"),
    ("镜前灯", "light", "mirror_light"),
    ("柜灯", "light", "cabinet_light"),
    ("灯", "light", "main"),
    ("空调", "climate", "ac"),
    ("温控器", "climate", "thermostat"),
    ("热水器", "switch", "water_heater"),
    ("插座", "switch", "socket"),
    ("空气净化器", "switch", "purifier_power"),
    ("香薰", "switch", "socket"),
    ("风扇", "fan", "standing_fan"),
    ("吊扇", "fan", "ceiling_fan"),
    ("排风扇", "fan", "exhaust_fan"),
    ("电视", "media_player", "tv"),
    ("音箱", "media_player", "speaker"),
    ("投影仪", "media_player", "projector"),
    ("门锁", "lock", "door_lock"),
    ("智能门锁", "lock", "smart_lock"),
    ("扫地机器人", "vacuum", "robot_vacuum"),
    ("加湿器", "humidifier", "humidifier"),
    ("除湿机", "dehumidifier", "dehumidifier"),
    ("人体传感器", "sensor", "motion"),
    ("温度传感器", "sensor", "temperature"),
    ("湿度传感器", "sensor", "humidity"),
    ("门磁", "sensor", "door"),
    ("窗磁", "sensor", "window"),
    ("漏水传感器", "sensor", "leak"),
    ("百叶帘", "cover", "blind"),
    ("遮阳帘", "cover", "shade"),
    ("窗帘", "cover", "curtain"),
]

OPEN_HINTS = (
    "turn on",
    "open",
    "start",
    "unlock",
    "run",
    "execute",
    "打开",
    "开启",
    "开",
    "启动",
    "解锁",
    "执行",
)
STOP_HINTS = (
    "turn off",
    "close",
    "stop",
    "lock",
    "shut down",
    "关闭",
    "关掉",
    "关",
    "停止",
    "锁上",
)
MOTION_ON_HINTS = (
    "someone is detected",
    "motion is detected",
    "when someone",
    "if someone",
    "有人",
    "有动静",
    "进门",
    "回家",
)
MOTION_OFF_HINTS = (
    "when no one",
    "after leaving",
    "leave",
    "离开",
    "人走了",
    "出门",
)


class MockLLMClient:
    """Heuristic mock LLM that handles both Chinese and English smart-home inputs."""

    def __init__(self, registry: DeviceRegistry | None = None) -> None:
        self.registry = registry or load_default_registry(PROJECT_ROOT)
        self.last_trace: dict[str, Any] = {}
        self._entity_index = self._build_entity_index()

    def generate(self, prompt: str) -> str:
        user_input = self._extract_user_input(prompt)
        payload, trace = self._build_response(user_input)
        self.last_trace = trace
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _extract_user_input(prompt: str) -> str:
        marker = "USER_INPUT:"
        if marker not in prompt:
            return ""
        return prompt.rsplit(marker, maxsplit=1)[-1].strip()

    def _build_entity_index(self) -> dict[str, list[str]]:
        room_tokens = sorted({token for _, token in ROOM_KEYWORDS}, key=len, reverse=True)
        index: dict[str, list[str]] = {}
        for device in self.registry.devices:
            entity_tail = device.entity_id.split(".", 1)[1]
            for room_token in room_tokens:
                prefix = f"{room_token}_"
                if entity_tail.startswith(prefix):
                    index.setdefault(room_token, []).append(device.entity_id)
                    break
        for room_token, entity_ids in index.items():
            index[room_token] = sorted(entity_ids)
        return index

    def _build_response(self, user_input: str) -> tuple[dict[str, Any], dict[str, Any]]:
        normalized = self._normalize_text(user_input)
        room_token = self._detect_room_token(normalized)
        used_fallback = False

        if self._is_conflicting_input(normalized):
            matched_pattern = "conflicting_actions"
            payload = self._conflicting_rule(room_token)
        elif self._has_invalid_weekday(normalized):
            matched_pattern = "invalid_weekday"
            payload = self._invalid_weekday_rule(room_token)
        elif self._has_invalid_time(normalized):
            matched_pattern = "invalid_time"
            payload = self._invalid_time_rule(user_input, room_token)
        elif self._is_sensor_control(normalized):
            matched_pattern = "sensor_control"
            payload = self._sensor_control_rule(room_token)
        elif self._is_humidity_rule(normalized):
            matched_pattern = "humidity_event"
            payload = self._humidity_event_rule(user_input, room_token)
        elif self._is_temperature_rule(normalized):
            matched_pattern = "temperature_event"
            payload = self._temperature_event_rule(user_input, room_token)
        elif self._contains_any(normalized, MOTION_ON_HINTS):
            matched_pattern = "motion_on"
            payload = self._state_rule(user_input, room_token, from_state="off", to_state="on")
        elif self._contains_any(normalized, MOTION_OFF_HINTS):
            matched_pattern = "motion_off"
            payload = self._state_rule(user_input, room_token, from_state="on", to_state="off")
        elif self._has_explicit_time(normalized):
            matched_pattern = "time_rule"
            payload = self._time_rule(user_input, room_token)
        else:
            matched_pattern = "manual_instruction"
            used_fallback = True
            payload = self._manual_rule(user_input, room_token)

        trace = {
            "used_fallback": used_fallback,
            "matched_pattern": matched_pattern,
            "detected_room_token": room_token,
            "selected_entities": [
                action.get("entity")
                for action in payload.get("actions", [])
                if isinstance(action, dict)
            ],
        }
        return payload, trace

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _detect_room_token(self, normalized: str) -> str:
        for keyword, token in ROOM_KEYWORDS:
            if keyword in normalized:
                return token
        for keyword, token in ROOM_FALLBACKS:
            if keyword in normalized:
                return token
        return "living_room"

    def _has_explicit_time(self, normalized: str) -> bool:
        return bool(
            re.search(r"\bat\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b", normalized)
            or re.search(r"\b\d{1,2}:\d{2}\s*(am|pm)?\b", normalized)
            or any(word in normalized for word in ("every day", "daily", "morning", "evening", "night", "早上", "晚上", "夜间", "每天"))
        )

    def _has_invalid_time(self, normalized: str) -> bool:
        if "25点" in normalized or "30点" in normalized:
            return True
        for match in re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", normalized):
            value = int(match.group(1))
            suffix = match.group(3)
            if suffix is None and value > 23:
                return True
        return False

    @staticmethod
    def _has_invalid_weekday(normalized: str) -> bool:
        return "周八" in normalized or "周九" in normalized or "weekday 8" in normalized

    def _is_conflicting_input(self, normalized: str) -> bool:
        patterns = (
            "同时打开和关闭",
            "又开灯又关灯",
            "open and close",
            "turn on and turn off",
            "both turn on and turn off",
        )
        return any(pattern in normalized for pattern in patterns)

    def _is_sensor_control(self, normalized: str) -> bool:
        sensor_keywords = ("sensor", "传感器")
        control_keywords = ("turn on", "turn off", "open", "close", "set", "打开", "关闭", "设置")
        return any(keyword in normalized for keyword in sensor_keywords) and any(
            keyword in normalized for keyword in control_keywords
        )

    def _is_humidity_rule(self, normalized: str) -> bool:
        humidity_event_keywords = (
            "humidity high",
            "high humidity",
            "湿度高",
            "太潮",
            "过于潮湿",
        )
        return any(word in normalized for word in humidity_event_keywords) and not any(
            word in normalized for word in ("set humidity", "set the humidity", "调整湿度")
        )

    def _is_temperature_rule(self, normalized: str) -> bool:
        return any(word in normalized for word in ("too hot", "temperature high", "温度高", "太热"))

    def _time_rule(self, text: str, room_token: str) -> dict[str, Any]:
        prefer_on = not self._contains_any(self._normalize_text(text), STOP_HINTS)
        return {
            "rule_name": f"{room_token}_time_rule",
            "trigger": {"type": "time", "at": self._parse_time(text)},
            "conditions": self._build_conditions(text),
            "actions": self._build_actions(text, room_token, prefer_on),
            "mode": "single",
        }

    def _manual_rule(self, text: str, room_token: str) -> dict[str, Any]:
        prefer_on = not self._contains_any(self._normalize_text(text), STOP_HINTS)
        return {
            "rule_name": f"{room_token}_manual_rule",
            "trigger": {
                "type": "event",
                "event_type": "manual_instruction",
                "event_data": {"source": "user_text"},
            },
            "conditions": [],
            "actions": self._build_actions(text, room_token, prefer_on),
            "mode": "single",
        }

    def _state_rule(self, text: str, room_token: str, from_state: str, to_state: str) -> dict[str, Any]:
        prefer_on = to_state == "on"
        return {
            "rule_name": f"{room_token}_state_rule",
            "trigger": {
                "type": "state_change",
                "entity": self._find_entity(room_token, "sensor", "motion")
                or self._find_entity(room_token, "sensor", "occupancy")
                or "sensor.entryway_motion",
                "from_state": from_state,
                "to_state": to_state,
            },
            "conditions": self._build_conditions(text),
            "actions": self._build_actions(text, room_token, prefer_on),
            "mode": "single",
        }

    def _humidity_event_rule(self, text: str, room_token: str) -> dict[str, Any]:
        humidity_sensor = self._find_entity(room_token, "sensor", "humidity") or "sensor.bathroom_humidity"
        target = self._find_entity(room_token, "dehumidifier", "dehumidifier") or self._find_entity(
            room_token, "switch", "water_heater"
        )
        target = target or "switch.bathroom_water_heater"
        return {
            "rule_name": f"{room_token}_humidity_rule",
            "trigger": {
                "type": "event",
                "event_type": "humidity_alert",
                "event_data": {"entity_id": humidity_sensor, "level": "high"},
            },
            "conditions": self._build_conditions(text),
            "actions": [{"service": self._service_for(target, prefer_on=True), "entity": target, "data": {}}],
            "mode": "single",
        }

    def _temperature_event_rule(self, text: str, room_token: str) -> dict[str, Any]:
        temperature_sensor = self._find_entity(room_token, "sensor", "temperature") or "sensor.living_room_temperature"
        climate_entity = self._find_entity(room_token, "climate", "ac") or "climate.living_room_ac"
        actions = [{"service": "climate.turn_on", "entity": climate_entity, "data": {}}]
        temperature = self._extract_temperature_value(text)
        if temperature is not None:
            actions.append(
                {
                    "service": "climate.set_temperature",
                    "entity": climate_entity,
                    "data": {"temperature": temperature},
                }
            )
        return {
            "rule_name": f"{room_token}_temperature_rule",
            "trigger": {
                "type": "event",
                "event_type": "temperature_alert",
                "event_data": {"entity_id": temperature_sensor, "level": "high"},
            },
            "conditions": self._build_conditions(text),
            "actions": actions,
            "mode": "single",
        }

    def _conflicting_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "light", "main") or self._find_entity(room_token, "cover", "curtain")
        entity = entity or "light.living_room_main"
        return {
            "rule_name": f"{room_token}_conflict_rule",
            "trigger": {
                "type": "event",
                "event_type": "manual_instruction",
                "event_data": {"source": "user_text"},
            },
            "conditions": [],
            "actions": [
                {"service": self._service_for(entity, prefer_on=True), "entity": entity, "data": {}},
                {"service": self._service_for(entity, prefer_on=False), "entity": entity, "data": {}},
            ],
            "mode": "single",
        }

    def _invalid_weekday_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "cover", "curtain") or self._find_entity(room_token, "light", "main")
        entity = entity or "light.living_room_main"
        return {
            "rule_name": f"{room_token}_invalid_weekday_rule",
            "trigger": {"type": "time", "at": "20:00:00"},
            "conditions": [{"type": "weekday", "days": ["mon", "someday"]}],
            "actions": [{"service": self._service_for(entity, prefer_on=False), "entity": entity, "data": {}}],
            "mode": "single",
        }

    def _invalid_time_rule(self, text: str, room_token: str) -> dict[str, Any]:
        prefer_on = not self._contains_any(self._normalize_text(text), STOP_HINTS)
        return {
            "rule_name": f"{room_token}_invalid_time_rule",
            "trigger": {"type": "time", "at": "25:00:00"},
            "conditions": [],
            "actions": self._build_actions(text, room_token, prefer_on),
            "mode": "single",
        }

    def _sensor_control_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "sensor", "motion") or self._find_entity(room_token, "sensor", "temperature")
        entity = entity or "sensor.living_room_temperature"
        return {
            "rule_name": f"{room_token}_sensor_control_rule",
            "trigger": {"type": "event", "event_type": "manual_instruction", "event_data": {"source": "user_text"}},
            "conditions": [],
            "actions": [{"service": "sensor.turn_on", "entity": entity, "data": {}}],
            "mode": "single",
        }

    def _build_actions(self, text: str, room_token: str, prefer_on: bool) -> list[dict[str, Any]]:
        normalized = self._normalize_text(text)
        matched_hints = [(domain, hint) for keyword, domain, hint in DEVICE_HINTS if keyword in normalized]
        if not matched_hints:
            matched_hints = [("light", "main")]

        actions: list[dict[str, Any]] = []
        seen_entities: set[str] = set()

        for domain, hint in matched_hints:
            entity = self._find_entity(room_token, domain, hint) or self._find_entity(room_token, domain)
            if entity is None or entity in seen_entities:
                continue
            seen_entities.add(entity)
            service, data = self._action_for(entity, normalized, prefer_on)
            actions.append({"service": service, "entity": entity, "data": data})

        if not actions:
            actions.append(
                {
                    "service": "light.turn_on" if prefer_on else "light.turn_off",
                    "entity": "light.living_room_main",
                    "data": {},
                }
            )

        return actions

    def _action_for(self, entity_id: str, normalized: str, prefer_on: bool) -> tuple[str, dict[str, Any]]:
        domain = entity_id.split(".", 1)[0]

        if domain == "climate" and any(word in normalized for word in ("temperature", "degrees", "温度", "度")):
            temperature = self._extract_temperature_value(normalized)
            if temperature is not None:
                return "climate.set_temperature", {"temperature": temperature}

        if domain in {"humidifier", "dehumidifier"} and any(
            word in normalized for word in ("humidity", "intensity", "mode", "湿度", "强度", "档位")
        ):
            humidity = self._extract_percentage_value(normalized)
            if humidity is not None:
                return "humidifier.set_humidity", {"humidity": humidity}
            return "humidifier.turn_on", {}

        if domain == "fan" and any(word in normalized for word in ("fan speed", "speed", "档位", "风速", "high", "medium", "low")):
            percentage = self._extract_fan_percentage(normalized)
            if percentage is not None:
                return "fan.set_percentage", {"percentage": percentage}

        if domain == "light" and any(word in normalized for word in ("brightness", "亮度")):
            brightness = self._extract_brightness_value(normalized)
            if brightness is not None:
                return "light.turn_on", {"brightness": brightness}
            return "light.turn_on", {}

        if domain == "cover":
            if any(word in normalized for word in ("close", "关闭", "拉上")):
                return "cover.close_cover", {}
            return "cover.open_cover", {}

        return self._service_for(entity_id, prefer_on), {}

    def _build_conditions(self, text: str) -> list[dict[str, Any]]:
        normalized = self._normalize_text(text)
        conditions: list[dict[str, Any]] = []

        if any(phrase in normalized for phrase in ("工作日", "周一到周五", "monday to friday", "weekdays")):
            conditions.append({"type": "weekday", "days": ["mon", "tue", "wed", "thu", "fri"]})
        elif any(phrase in normalized for phrase in ("周末", "weekend", "weekends")):
            conditions.append({"type": "weekday", "days": ["sat", "sun"]})

        if any(word in normalized for word in ("晚上", "夜间", "夜里", "sleep", "bedtime", "evening", "night")):
            conditions.append({"type": "time_range", "start": "18:00:00", "end": "23:59:59"})
        elif any(word in normalized for word in ("早上", "清晨", "morning")):
            conditions.append({"type": "time_range", "start": "06:00:00", "end": "09:00:00"})

        return conditions

    def _find_entity(self, room_token: str, domain: str, hint: str | None = None) -> str | None:
        candidates = [
            entity_id
            for entity_id in self._entity_index.get(room_token, [])
            if entity_id.startswith(f"{domain}.")
        ]
        if hint is not None:
            hinted = [entity_id for entity_id in candidates if hint in entity_id]
            if hinted:
                return hinted[0]
        return candidates[0] if candidates else None

    @staticmethod
    def _service_for(entity_id: str, prefer_on: bool) -> str:
        domain = entity_id.split(".", 1)[0]
        on_map = {
            "light": "light.turn_on",
            "climate": "climate.turn_on",
            "switch": "switch.turn_on",
            "cover": "cover.open_cover",
            "fan": "fan.turn_on",
            "media_player": "media_player.turn_on",
            "lock": "lock.unlock",
            "vacuum": "vacuum.start",
            "humidifier": "humidifier.turn_on",
            "dehumidifier": "humidifier.turn_on",
            "scene": "scene.turn_on",
            "script": "script.turn_on",
            "siren": "siren.turn_on",
        }
        off_map = {
            "light": "light.turn_off",
            "climate": "climate.turn_off",
            "switch": "switch.turn_off",
            "cover": "cover.close_cover",
            "fan": "fan.turn_off",
            "media_player": "media_player.turn_off",
            "lock": "lock.lock",
            "vacuum": "vacuum.stop",
            "humidifier": "humidifier.turn_off",
            "dehumidifier": "humidifier.turn_off",
            "scene": "scene.turn_on",
            "script": "script.turn_on",
            "siren": "siren.turn_off",
        }
        if prefer_on:
            return on_map.get(domain, "light.turn_on")
        return off_map.get(domain, "light.turn_off")

    def _parse_time(self, text: str) -> str:
        normalized = self._normalize_text(text)
        match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", normalized)
        if not match:
            match = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", normalized)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            suffix = match.group(3)
            if suffix == "pm" and hour < 12:
                hour += 12
            if suffix == "am" and hour == 12:
                hour = 0
            hour = max(0, min(hour, 23))
            return f"{hour:02d}:{minute:02d}:00"

        zh_match = re.search(r"(\d{1,2})点(半)?", text)
        if zh_match:
            hour = max(0, min(int(zh_match.group(1)), 23))
            minute = 30 if zh_match.group(2) else 0
            return f"{hour:02d}:{minute:02d}:00"

        if any(word in normalized for word in ("morning", "早上", "清晨")):
            return "07:00:00"
        if any(word in normalized for word in ("evening", "晚上")):
            return "20:00:00"
        if any(word in normalized for word in ("night", "夜间", "夜里")):
            return "22:00:00"
        return "20:00:00"

    @staticmethod
    def _extract_temperature_value(text: str) -> int | None:
        match = re.search(r"(\d{1,2})\s*(degrees?|度)", text)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_percentage_value(text: str) -> int | None:
        match = re.search(r"(\d{1,3})\s*%?", text)
        if not match:
            return None
        value = int(match.group(1))
        return max(0, min(value, 100))

    def _extract_brightness_value(self, text: str) -> int | None:
        if "decrease" in text or "降低" in text:
            value = self._extract_percentage_value(text)
            if value is not None:
                return max(1, 100 - value)
        if "increase" in text or "提高" in text:
            value = self._extract_percentage_value(text)
            if value is not None:
                return min(100, value)
        return self._extract_percentage_value(text)

    def _extract_fan_percentage(self, text: str) -> int | None:
        if "high" in text or "高速" in text:
            return 100
        if "medium" in text or "中速" in text:
            return 60
        if "low" in text or "低速" in text:
            return 30
        return self._extract_percentage_value(text)


if __name__ == "__main__":
    client = MockLLMClient()
    prompt = "USER_INPUT: Set the temperature of the heating system in the master bedroom to 20 degrees."
    print(client.generate(prompt))
    print(json.dumps(client.last_trace, ensure_ascii=False, indent=2))
