from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from models.device_models import DeviceRegistry, load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent

ROOM_TOKEN_MAP = {
    "客厅": "living_room",
    "主卧": "master_bedroom",
    "次卧": "guest_bedroom",
    "卧室": "bedroom",
    "儿童房": "kids_room",
    "书房": "study",
    "厨房": "kitchen",
    "餐厅": "dining_room",
    "卫生间": "bathroom",
    "主卫": "master_bathroom",
    "次卫": "guest_bathroom",
    "阳台": "balcony",
    "玄关": "entryway",
    "走廊": "hallway",
    "储物间": "storage_room",
    "衣帽间": "closet",
    "洗衣房": "laundry_room",
    "车库": "garage",
    "地下室": "basement",
    "花园": "garden",
}

ROOM_FALLBACKS = {
    "进门": "玄关",
    "回家": "玄关",
    "出门": "玄关",
    "睡觉": "卧室",
    "洗澡": "卫生间",
    "做饭": "厨房",
}

DEVICE_HINTS = {
    "主灯": ("light", "main"),
    "灯带": ("light", "strip"),
    "台灯": ("light", "lamp"),
    "吸顶灯": ("light", "ceiling"),
    "壁灯": ("light", "wall"),
    "夜灯": ("light", "night_light"),
    "落地灯": ("light", "floor_lamp"),
    "书桌灯": ("light", "desk_lamp"),
    "镜前灯": ("light", "mirror_light"),
    "柜灯": ("light", "cabinet_light"),
    "灯": ("light", "main"),
    "窗帘": ("cover", "curtain"),
    "百叶帘": ("cover", "blind"),
    "遮阳帘": ("cover", "shade"),
    "空调": ("climate", "ac"),
    "温控器": ("climate", "thermostat"),
    "热水器": ("switch", "water_heater"),
    "插座": ("switch", "socket"),
    "空气净化器": ("switch", "purifier_power"),
    "香薰": ("switch", "socket"),
    "咖啡机": ("switch", "coffee_machine"),
    "电饭煲": ("switch", "rice_cooker"),
    "热水壶": ("switch", "kettle"),
    "洗衣机": ("switch", "washer_power"),
    "烘干机": ("switch", "dryer_power"),
    "风扇": ("fan", "standing_fan"),
    "吊扇": ("fan", "ceiling_fan"),
    "排风扇": ("fan", "exhaust_fan"),
    "电视": ("media_player", "tv"),
    "音箱": ("media_player", "speaker"),
    "投影仪": ("media_player", "projector"),
    "门锁": ("lock", "door_lock"),
    "智能门锁": ("lock", "smart_lock"),
    "扫地机器人": ("vacuum", "robot_vacuum"),
    "加湿器": ("humidifier", "humidifier"),
    "除湿机": ("dehumidifier", "dehumidifier"),
    "摄像头": ("camera", "indoor_cam"),
    "传感器": ("sensor", "motion"),
    "人体传感器": ("sensor", "motion"),
    "温度传感器": ("sensor", "temperature"),
    "湿度传感器": ("sensor", "humidity"),
    "门磁": ("sensor", "door"),
    "窗磁": ("sensor", "window"),
    "漏水传感器": ("sensor", "leak"),
}

OPEN_WORDS = ("打开", "开启", "开", "解锁", "启动", "执行")
CLOSE_WORDS = ("关闭", "关掉", "关", "锁上", "停止")


class MockLLMClient:
    """Heuristic local mock that scales to large device registries."""

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
        room_tokens = sorted(ROOM_TOKEN_MAP.values(), key=len, reverse=True)
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
        room = self._detect_room(user_input)
        room_token = ROOM_TOKEN_MAP.get(room, "living_room")
        used_fallback = False
        matched_pattern = "time_rule"

        if any(phrase in user_input for phrase in ("同时打开和关闭", "又开灯又关灯", "打开并立刻关闭")):
            matched_pattern = "conflicting_actions"
            payload = self._conflicting_rule(room_token)
        elif "周八" in user_input or "周九" in user_input:
            matched_pattern = "invalid_weekday"
            payload = self._invalid_weekday_rule(room_token)
        elif "25点" in user_input or "三十点" in user_input:
            matched_pattern = "invalid_time"
            payload = self._invalid_time_rule(user_input, room_token)
        elif "传感器" in user_input and any(word in user_input for word in OPEN_WORDS + CLOSE_WORDS):
            matched_pattern = "sensor_control"
            payload = self._sensor_control_rule(room_token)
        elif any(word in user_input for word in ("湿度高", "潮", "太潮")):
            matched_pattern = "humidity_event"
            payload = self._humidity_event_rule(room_token)
        elif any(word in user_input for word in ("太热", "热了", "温度高")):
            matched_pattern = "temperature_event"
            payload = self._temperature_event_rule(user_input, room_token)
        elif any(word in user_input for word in ("有人", "有动静", "进门", "回家")):
            matched_pattern = "motion_on"
            payload = self._state_rule(user_input, room_token, from_state="off", to_state="on")
        elif any(word in user_input for word in ("离开", "人走了", "出门")):
            matched_pattern = "motion_off"
            payload = self._state_rule(user_input, room_token, from_state="on", to_state="off")
        else:
            used_fallback = True
            payload = self._time_rule(user_input, room_token)

        trace = {
            "used_fallback": used_fallback,
            "matched_pattern": matched_pattern,
            "detected_room": room,
            "detected_room_token": room_token,
            "selected_entities": [action.get("entity") for action in payload.get("actions", []) if isinstance(action, dict)],
        }
        return payload, trace

    def _detect_room(self, text: str) -> str:
        for room in ROOM_TOKEN_MAP:
            if room in text:
                return room
        for keyword, room in ROOM_FALLBACKS.items():
            if keyword in text:
                return room
        return "客厅"

    def _time_rule(self, text: str, room_token: str) -> dict[str, Any]:
        prefer_on = not any(word in text for word in CLOSE_WORDS)
        return {
            "rule_name": f"{room_token}_time_rule",
            "trigger": {"type": "time", "at": self._parse_time(text)},
            "conditions": self._build_conditions(text),
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

    def _humidity_event_rule(self, room_token: str) -> dict[str, Any]:
        humidity_sensor = self._find_entity(room_token, "sensor", "humidity") or "sensor.bathroom_humidity"
        target = self._find_entity(room_token, "switch", "water_heater") or self._find_entity(room_token, "dehumidifier", "dehumidifier")
        service = self._service_for(target or "switch.bathroom_water_heater", prefer_on=True)
        return {
            "rule_name": f"{room_token}_humidity_rule",
            "trigger": {
                "type": "event",
                "event_type": "humidity_alert",
                "event_data": {"entity_id": humidity_sensor, "level": "high"},
            },
            "conditions": [],
            "actions": [{"service": service, "entity": target or "switch.bathroom_water_heater", "data": {}}],
            "mode": "single",
        }

    def _temperature_event_rule(self, text: str, room_token: str) -> dict[str, Any]:
        temp_sensor = self._find_entity(room_token, "sensor", "temperature") or "sensor.living_room_temperature"
        climate = self._find_entity(room_token, "climate", "ac") or "climate.living_room_ac"
        actions = [{"service": "climate.turn_on", "entity": climate, "data": {}}]
        temperature = self._extract_temperature_value(text)
        if temperature is not None:
            actions.append({"service": "climate.set_temperature", "entity": climate, "data": {"temperature": temperature}})
        return {
            "rule_name": f"{room_token}_temperature_rule",
            "trigger": {
                "type": "event",
                "event_type": "temperature_alert",
                "event_data": {"entity_id": temp_sensor, "level": "high"},
            },
            "conditions": [],
            "actions": actions,
            "mode": "single",
        }

    def _conflicting_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "light", "main") or self._find_entity(room_token, "cover", "curtain") or "light.living_room_main"
        open_service = self._service_for(entity, prefer_on=True)
        close_service = self._service_for(entity, prefer_on=False)
        return {
            "rule_name": f"{room_token}_conflict_rule",
            "trigger": {
                "type": "state_change",
                "entity": self._find_entity(room_token, "sensor", "motion") or "sensor.entryway_motion",
                "from_state": "off",
                "to_state": "on",
            },
            "conditions": [],
            "actions": [
                {"service": open_service, "entity": entity, "data": {}},
                {"service": close_service, "entity": entity, "data": {}},
            ],
            "mode": "single",
        }

    def _invalid_weekday_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "cover", "curtain") or self._find_entity(room_token, "light", "main") or "light.living_room_main"
        return {
            "rule_name": f"{room_token}_invalid_weekday_rule",
            "trigger": {"type": "time", "at": "20:00:00"},
            "conditions": [{"type": "weekday", "days": ["mon", "someday"]}],
            "actions": [{"service": self._service_for(entity, prefer_on=False), "entity": entity, "data": {}}],
            "mode": "single",
        }

    def _invalid_time_rule(self, text: str, room_token: str) -> dict[str, Any]:
        prefer_on = not any(word in text for word in CLOSE_WORDS)
        return {
            "rule_name": f"{room_token}_invalid_time_rule",
            "trigger": {"type": "time", "at": "25:00:00"},
            "conditions": [],
            "actions": self._build_actions(text, room_token, prefer_on),
            "mode": "single",
        }

    def _sensor_control_rule(self, room_token: str) -> dict[str, Any]:
        entity = self._find_entity(room_token, "sensor", "motion") or self._find_entity(room_token, "sensor", "temperature") or "sensor.living_room_temperature"
        return {
            "rule_name": f"{room_token}_sensor_control_rule",
            "trigger": {"type": "time", "at": "08:00:00"},
            "conditions": [],
            "actions": [{"service": "sensor.turn_on", "entity": entity, "data": {}}],
            "mode": "single",
        }

    def _build_actions(self, text: str, room_token: str, prefer_on: bool) -> list[dict[str, Any]]:
        matched: list[tuple[str, str]] = []
        for keyword, (domain, hint) in DEVICE_HINTS.items():
            if keyword in text:
                matched.append((domain, hint))

        if not matched:
            matched.append(("light", "main"))

        actions: list[dict[str, Any]] = []
        seen_entities: set[str] = set()

        for domain, hint in matched:
            entity = self._find_entity(room_token, domain, hint) or self._find_entity(room_token, domain)
            if entity is None or entity in seen_entities:
                continue
            seen_entities.add(entity)
            service = self._service_for(entity, prefer_on=prefer_on)
            data: dict[str, Any] = {}
            if service == "climate.set_temperature":
                temperature = self._extract_temperature_value(text)
                if temperature is not None:
                    data = {"temperature": temperature}
            actions.append({"service": service, "entity": entity, "data": data})

        if not actions:
            actions.append({"service": "light.turn_on" if prefer_on else "light.turn_off", "entity": "light.living_room_main", "data": {}})

        if "空调" in text and "度" in text:
            climate_entity = next((action["entity"] for action in actions if action["entity"].startswith("climate.")), None)
            temperature = self._extract_temperature_value(text)
            if climate_entity and temperature is not None and not any(
                action["service"] == "climate.set_temperature" for action in actions
            ):
                actions.append(
                    {
                        "service": "climate.set_temperature",
                        "entity": climate_entity,
                        "data": {"temperature": temperature},
                    }
                )

        return actions

    def _build_conditions(self, text: str) -> list[dict[str, Any]]:
        conditions: list[dict[str, Any]] = []
        if "工作日" in text or "周一到周五" in text:
            conditions.append({"type": "weekday", "days": ["mon", "tue", "wed", "thu", "fri"]})
        elif "周末" in text:
            conditions.append({"type": "weekday", "days": ["sat", "sun"]})

        if any(word in text for word in ("晚上", "夜里", "傍晚", "睡前", "天黑")):
            conditions.append({"type": "time_range", "start": "18:00:00", "end": "23:59:59"})
        elif any(word in text for word in ("早上", "清晨", "早晨")):
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

    def _service_for(self, entity_id: str, prefer_on: bool) -> str:
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
        return on_map.get(domain, "light.turn_on") if prefer_on else off_map.get(domain, "light.turn_off")

    def _parse_time(self, text: str) -> str:
        match = re.search(r"(\d{1,2})点(?:(\d{1,2})分|半)?", text)
        if match:
            hour = int(match.group(1))
            minute = 30 if "半" in match.group(0) else int(match.group(2) or 0)
            return f"{hour:02d}:{minute:02d}:00"
        if "早上" in text or "清晨" in text or "早晨" in text:
            return "07:00:00"
        if "晚上" in text:
            return "20:00:00"
        if "夜间" in text or "夜里" in text:
            return "22:00:00"
        return "20:00:00"

    def _extract_temperature_value(self, text: str) -> int | None:
        match = re.search(r"(\d{2})\s*度", text)
        if match:
            return int(match.group(1))
        return None


if __name__ == "__main__":
    client = MockLLMClient()
    prompt = "USER_INPUT: 玄关有人时开灯"
    print(client.generate(prompt))
    print(json.dumps(client.last_trace, ensure_ascii=False, indent=2))
