from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from models.device_models import load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = PROJECT_ROOT / "data" / "test_cases"
OUTPUT_PATH = PROJECT_ROOT / "data" / "gold_dsl.json"

KEEP_ORIGINAL_COUNT = 100
MODIFY_EXISTING_COUNT = 400
NEW_RECORD_COUNT = 200
RANDOM_SEED = 42

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

DEVICE_KEYWORDS = [
    ("智能门锁", "lock", "smart_lock", "门锁"),
    ("门锁", "lock", "door_lock", "门锁"),
    ("扫地机器人", "vacuum", "robot_vacuum", "扫地机器人"),
    ("空气净化器", "switch", "purifier_power", "空气净化器"),
    ("咖啡机", "switch", "coffee_machine", "咖啡机"),
    ("电饭煲", "switch", "rice_cooker", "电饭煲"),
    ("热水壶", "switch", "kettle", "热水壶"),
    ("洗衣机", "switch", "washer_power", "洗衣机"),
    ("烘干机", "switch", "dryer_power", "烘干机"),
    ("热水器", "switch", "water_heater", "热水器"),
    ("插座", "switch", "socket", "插座"),
    ("加湿器", "humidifier", "humidifier", "加湿器"),
    ("除湿机", "dehumidifier", "dehumidifier", "除湿机"),
    ("投影仪", "media_player", "projector", "投影仪"),
    ("音箱", "media_player", "speaker", "音箱"),
    ("电视", "media_player", "tv", "电视"),
    ("吊扇", "fan", "ceiling_fan", "吊扇"),
    ("排风扇", "fan", "exhaust_fan", "排风扇"),
    ("风扇", "fan", "standing_fan", "风扇"),
    ("吸顶灯", "light", "ceiling", "吸顶灯"),
    ("壁灯", "light", "wall", "壁灯"),
    ("落地灯", "light", "floor_lamp", "落地灯"),
    ("书桌灯", "light", "desk_lamp", "书桌灯"),
    ("台灯", "light", "lamp", "台灯"),
    ("夜灯", "light", "night_light", "夜灯"),
    ("灯带", "light", "strip", "灯带"),
    ("镜前灯", "light", "mirror_light", "镜前灯"),
    ("柜灯", "light", "cabinet_light", "柜灯"),
    ("主灯", "light", "main", "主灯"),
    ("灯", "light", "main", "灯"),
    ("窗帘", "cover", "curtain", "窗帘"),
    ("百叶帘", "cover", "blind", "百叶帘"),
    ("遮阳帘", "cover", "shade", "遮阳帘"),
    ("空调", "climate", "ac", "空调"),
    ("温控器", "climate", "thermostat", "温控器"),
    ("模式", "scene", "relax_mode", "场景"),
    ("脚本", "script", "night_shutdown", "脚本"),
]

OPEN_WORDS = ("打开", "开启", "亮起来", "执行", "启动", "拉开", "升起", "开起来")
CLOSE_WORDS = ("关闭", "关掉", "停掉", "停止", "收起", "拉上")

NEW_INPUT_TEMPLATES = [
    "{room}有人时打开{device}",
    "离开{room}后关闭{device}",
    "每天早上7点打开{room}{device}",
    "每天晚上10点关闭{room}{device}",
    "工作日早上8点打开{room}{device}",
    "周末晚上9点关闭{room}{device}",
    "{room}太热了就把{device}开起来",
    "{room}湿度高时打开{device}",
    "天黑以后打开{room}{device}",
    "回家时执行{room}{device}",
]


class IndependentGoldAnnotator:
    """Independent heuristic annotator intentionally different from pipeline output style."""

    def __init__(self) -> None:
        self.registry = load_default_registry(PROJECT_ROOT)
        self.entity_index = self._build_entity_index()

    def annotate(self, input_text: str) -> dict[str, Any]:
        room = self._detect_room(input_text)
        room_token = ROOM_TOKEN_MAP[room]
        trigger = self._build_trigger(input_text, room, room_token)
        conditions = self._build_conditions(input_text, trigger)
        actions = self._build_actions(input_text, room, room_token)
        mode = self._select_mode(trigger, actions)
        return {
            "rule_name": self._build_rule_name(input_text, room, trigger, actions),
            "trigger": trigger,
            "conditions": conditions,
            "actions": actions,
            "mode": mode,
        }

    def _build_entity_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}
        room_tokens = sorted(ROOM_TOKEN_MAP.values(), key=len, reverse=True)
        for device in self.registry.devices:
            tail = device.entity_id.split(".", 1)[1]
            for room_token in room_tokens:
                prefix = f"{room_token}_"
                if tail.startswith(prefix):
                    index.setdefault(room_token, []).append(device.entity_id)
                    break
        for key in index:
            index[key] = sorted(index[key])
        return index

    def _detect_room(self, text: str) -> str:
        for room in ROOM_TOKEN_MAP:
            if room in text:
                return room
        for keyword, room in ROOM_FALLBACKS.items():
            if keyword in text:
                return room
        return "客厅"

    def _build_trigger(self, text: str, room: str, room_token: str) -> dict[str, Any]:
        if any(word in text for word in ("太热", "热了", "温度高")):
            return {
                "type": "event",
                "event_type": "temperature_alert",
                "event_data": {
                    "entity_id": self._find_entity(room_token, "sensor", "temperature") or "sensor.living_room_temperature",
                    "level": "high",
                },
            }
        if any(word in text for word in ("湿度高", "太潮", "潮湿")):
            return {
                "type": "event",
                "event_type": "humidity_alert",
                "event_data": {
                    "entity_id": self._find_entity(room_token, "sensor", "humidity") or "sensor.bathroom_humidity",
                    "level": "high",
                },
            }
        if any(word in text for word in ("有人", "有动静", "回家", "进门")):
            return {
                "type": "state_change",
                "entity": self._find_entity(room_token, "sensor", "motion") or "sensor.entryway_motion",
                "from_state": "off",
                "to_state": "on",
            }
        if any(word in text for word in ("离开", "出门", "人走了")):
            return {
                "type": "state_change",
                "entity": self._find_entity(room_token, "sensor", "motion") or "sensor.entryway_motion",
                "from_state": "on",
                "to_state": "off",
            }
        return {"type": "time", "at": self._parse_time(text)}

    def _build_conditions(self, text: str, trigger: dict[str, Any]) -> list[dict[str, Any]]:
        conditions: list[dict[str, Any]] = []
        if "工作日" in text or "周一到周五" in text:
            conditions.append({"type": "weekday", "days": ["mon", "tue", "wed", "thu", "fri"]})
        elif "周末" in text:
            conditions.append({"type": "weekday", "days": ["sat", "sun"]})

        if trigger.get("type") != "time":
            if any(word in text for word in ("晚上", "夜里", "夜间", "天黑以后", "睡前")):
                conditions.append({"type": "time_range", "start": "18:00:00", "end": "23:59:59"})
            elif any(word in text for word in ("早上", "清晨", "早晨")):
                conditions.append({"type": "time_range", "start": "06:00:00", "end": "09:00:00"})
        return conditions

    def _build_actions(self, text: str, room: str, room_token: str) -> list[dict[str, Any]]:
        matched_specs = self._extract_target_specs(text)
        if not matched_specs:
            matched_specs = [("light", "main", "灯")]

        prefer_on = not any(word in text for word in CLOSE_WORDS)
        actions: list[dict[str, Any]] = []
        seen_entities: set[str] = set()

        for domain, hint, label in matched_specs:
            entity = self._resolve_entity(room_token, domain, hint, label)
            if entity is None or entity in seen_entities:
                continue
            seen_entities.add(entity)
            service = self._select_service(entity, text, prefer_on)
            data: dict[str, Any] = {}
            if entity.startswith("light.") and any(word in text for word in ("亮一点", "调亮", "亮些")):
                data = {"brightness": 180}
            if service == "climate.set_temperature":
                temperature = self._extract_temperature(text)
                if temperature is not None:
                    data = {"temperature": temperature}
            actions.append({"service": service, "entity": entity, "data": data})

        climate_entities = [action["entity"] for action in actions if action["entity"].startswith("climate.")]
        if climate_entities:
            temperature = self._extract_temperature(text)
            if temperature is not None and not any(action["service"] == "climate.set_temperature" for action in actions):
                actions.append(
                    {
                        "service": "climate.set_temperature",
                        "entity": climate_entities[0],
                        "data": {"temperature": temperature},
                    }
                )

        if not actions:
            default_entity = self._find_entity(room_token, "light", "main") or "light.living_room_main"
            actions.append(
                {
                    "service": self._select_service(default_entity, text, prefer_on),
                    "entity": default_entity,
                    "data": {},
                }
            )
        return actions

    def _select_mode(self, trigger: dict[str, Any], actions: list[dict[str, Any]]) -> str:
        if len(actions) >= 2:
            return "queued"
        if trigger.get("type") in {"state_change", "event"}:
            return "restart"
        return "single"

    def _build_rule_name(self, text: str, room: str, trigger: dict[str, Any], actions: list[dict[str, Any]]) -> str:
        action_label = self._label_for_entity(actions[0]["entity"]) if actions else "设备"
        if trigger.get("type") == "state_change":
            return f"{room}感应控制{action_label}"
        if trigger.get("type") == "event" and trigger.get("event_type") == "temperature_alert":
            return f"{room}高温处理{action_label}"
        if trigger.get("type") == "event" and trigger.get("event_type") == "humidity_alert":
            return f"{room}湿度处理{action_label}"
        return f"{room}定时{self._verb_from_text(text)}{action_label}"

    def _verb_from_text(self, text: str) -> str:
        return "关闭" if any(word in text for word in CLOSE_WORDS) else "开启"

    def _extract_target_specs(self, text: str) -> list[tuple[str, str, str]]:
        matched: list[tuple[str, str, str]] = []
        consumed_labels: set[str] = set()
        has_specific_light = any(keyword in text for keyword, domain, _, _ in DEVICE_KEYWORDS if domain == "light" and keyword != "灯")
        for keyword, domain, hint, label in DEVICE_KEYWORDS:
            if keyword == "灯" and has_specific_light:
                continue
            if keyword in text and label not in consumed_labels:
                matched.append((domain, hint, label))
                consumed_labels.add(label)
        return matched

    def _resolve_entity(self, room_token: str, domain: str, hint: str, label: str) -> str | None:
        if domain == "script":
            script_hint = self._choose_script_hint(label)
            return self._find_entity(room_token, domain, script_hint) or self._find_entity(room_token, domain)
        if domain == "scene":
            scene_hint = self._choose_scene_hint(label)
            return self._find_entity(room_token, domain, scene_hint) or self._find_entity(room_token, domain)
        return self._find_entity(room_token, domain, hint) or self._find_entity(room_token, domain)

    def _choose_script_hint(self, _: str) -> str:
        return "night_shutdown"

    def _choose_scene_hint(self, _: str) -> str:
        return "relax_mode"

    def _find_entity(self, room_token: str, domain: str, hint: str | None = None) -> str | None:
        candidates = [
            entity_id
            for entity_id in self.entity_index.get(room_token, [])
            if entity_id.startswith(f"{domain}.")
        ]
        if hint:
            for entity_id in candidates:
                if hint in entity_id:
                    return entity_id
        return candidates[0] if candidates else None

    def _select_service(self, entity_id: str, text: str, prefer_on: bool) -> str:
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
        if domain == "climate" and self._extract_temperature(text) is not None:
            return "climate.turn_on"
        if any(word in text for word in CLOSE_WORDS):
            return off_map.get(domain, "light.turn_off")
        if any(word in text for word in OPEN_WORDS):
            return on_map.get(domain, "light.turn_on")
        return on_map.get(domain, "light.turn_on") if prefer_on else off_map.get(domain, "light.turn_off")

    def _label_for_entity(self, entity_id: str) -> str:
        tail = entity_id.split(".", 1)[1]
        if "curtain" in tail:
            return "窗帘"
        if "blind" in tail:
            return "百叶帘"
        if "shade" in tail:
            return "遮阳帘"
        if "ceiling_fan" in tail:
            return "吊扇"
        if "standing_fan" in tail:
            return "风扇"
        if "ac" in tail:
            return "空调"
        if "thermostat" in tail:
            return "温控器"
        if "water_heater" in tail:
            return "热水器"
        if "socket" in tail:
            return "插座"
        if "tv" in tail:
            return "电视"
        if "speaker" in tail:
            return "音箱"
        if "door_lock" in tail or "smart_lock" in tail:
            return "门锁"
        if "night_shutdown" in tail:
            return "脚本"
        if "relax_mode" in tail:
            return "场景"
        if "main" in tail:
            return "主灯"
        if "lamp" in tail:
            return "台灯"
        return "设备"

    def _parse_time(self, text: str) -> str:
        match = re.search(r"(\d{1,2})点(?:(\d{1,2})分|半)?", text)
        if match:
            hour = int(match.group(1))
            minute = 30 if "半" in match.group(0) else int(match.group(2) or 0)
            if any(word in text for word in ("晚上", "夜里", "夜间")) and 0 <= hour < 12:
                hour += 12
            hour = max(0, min(hour, 23))
            minute = max(0, min(minute, 59))
            return f"{hour:02d}:{minute:02d}:00"
        if "早上" in text or "清晨" in text or "早晨" in text:
            return "07:00:00"
        if "晚上" in text:
            return "20:00:00"
        if "夜里" in text or "夜间" in text:
            return "22:00:00"
        if "天黑以后" in text:
            return "18:30:00"
        return "20:00:00"

    def _extract_temperature(self, text: str) -> int | None:
        match = re.search(r"(\d{2})\s*度", text)
        return int(match.group(1)) if match else None


def load_existing_gold() -> list[dict[str, Any]]:
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    return [item for item in payload if isinstance(item, dict)]


def load_case_pool() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for file_name in ("normal_cases.json", "ambiguous_cases.json"):
        path = TEST_CASE_DIR / file_name
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(item for item in payload if isinstance(item, dict))
    return cases


def generate_new_inputs(existing_inputs: set[str], count: int, rng: random.Random) -> list[str]:
    rooms = list(ROOM_TOKEN_MAP.keys())
    devices = [
        "主灯", "台灯", "窗帘", "空调", "风扇", "吊扇", "热水器", "插座", "音箱", "电视",
        "百叶帘", "夜灯", "门锁", "脚本", "模式",
    ]
    generated: list[str] = []
    seen = set(existing_inputs)
    attempts = 0
    while len(generated) < count and attempts < count * 50:
        attempts += 1
        template = rng.choice(NEW_INPUT_TEMPLATES)
        room = rng.choice(rooms)
        device = rng.choice(devices)
        candidate = template.format(room=room, device=device)
        if candidate in seen:
            continue
        seen.add(candidate)
        generated.append(candidate)
    return generated


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    annotator = IndependentGoldAnnotator()
    existing = load_existing_gold()
    case_pool = load_case_pool()

    if len(existing) < KEEP_ORIGINAL_COUNT + MODIFY_EXISTING_COUNT:
        raise ValueError("Current gold_dsl.json does not contain enough records.")

    scored_existing = sorted(existing, key=lambda item: _keep_score(item), reverse=True)
    kept_records = scored_existing[:KEEP_ORIGINAL_COUNT]
    records_to_modify = scored_existing[KEEP_ORIGINAL_COUNT : KEEP_ORIGINAL_COUNT + MODIFY_EXISTING_COUNT]

    modified_records = [
        {
            "input_text": record["input_text"],
            "gold_dsl": annotator.annotate(record["input_text"]),
        }
        for record in records_to_modify
    ]

    used_inputs = {record["input_text"] for record in existing}
    remaining_pool = [
        case["input_text"]
        for case in case_pool
        if case["input_text"] not in used_inputs
    ]
    rng.shuffle(remaining_pool)
    new_inputs = remaining_pool[: max(0, NEW_RECORD_COUNT - 100)]
    synthetic_inputs = generate_new_inputs(set(used_inputs) | set(new_inputs), NEW_RECORD_COUNT - len(new_inputs), rng)
    all_new_inputs = new_inputs + synthetic_inputs

    new_records = [{"input_text": text, "gold_dsl": annotator.annotate(text)} for text in all_new_inputs]

    final_records = kept_records + modified_records + new_records
    OUTPUT_PATH.write_text(json.dumps(final_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Generated {len(final_records)} gold records: "
        f"{len(kept_records)} kept, {len(modified_records)} modified, {len(new_records)} new."
    )


def _keep_score(record: dict[str, Any]) -> int:
    text = record.get("input_text", "")
    gold = record.get("gold_dsl", {})
    actions = gold.get("actions", []) if isinstance(gold, dict) else []
    first_entity = actions[0].get("entity", "") if actions and isinstance(actions[0], dict) else ""
    score = 0
    if "窗帘" in text and "curtain" in first_entity:
        score += 3
    if "空调" in text and first_entity.startswith("climate."):
        score += 3
    if ("风扇" in text or "吊扇" in text) and first_entity.startswith("fan."):
        score += 3
    if "灯" in text and first_entity.startswith("light."):
        score += 2
    if "热水器" in text and "water_heater" in first_entity:
        score += 2
    if any(word in text for word in ("有人", "离开", "回家", "出门")) and gold.get("trigger", {}).get("type") == "state_change":
        score += 1
    if any(word in text for word in ("太热", "温度高", "湿度高")) and gold.get("trigger", {}).get("type") == "event":
        score += 1
    if any(word in text for word in ("每天", "早上", "晚上", "天黑以后", "点")) and gold.get("trigger", {}).get("type") == "time":
        score += 1
    return score


if __name__ == "__main__":
    main()
