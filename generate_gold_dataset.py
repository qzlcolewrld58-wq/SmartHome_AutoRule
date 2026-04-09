from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from models.device_models import load_default_registry


PROJECT_ROOT = Path(__file__).resolve().parent
TEST_CASE_DIR = PROJECT_ROOT / "data" / "test_cases"
OUTPUT_PATH = PROJECT_ROOT / "data" / "gold_dsl.json"

RANDOM_SEED = 42
TARGET_RECORD_COUNT = 1800

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
    "回家": "玄关",
    "进门": "玄关",
    "出门": "玄关",
    "睡觉": "卧室",
    "洗澡": "卫生间",
    "做饭": "厨房",
    "看书": "书房",
    "观影": "客厅",
}

DEVICE_KEYWORDS = [
    ("主灯", "light", "main", "主灯"),
    ("灯带", "light", "strip", "灯带"),
    ("台灯", "light", "lamp", "台灯"),
    ("吸顶灯", "light", "ceiling", "吸顶灯"),
    ("壁灯", "light", "wall", "壁灯"),
    ("夜灯", "light", "night_light", "夜灯"),
    ("落地灯", "light", "floor_lamp", "落地灯"),
    ("书桌灯", "light", "desk_lamp", "书桌灯"),
    ("镜前灯", "light", "mirror_light", "镜前灯"),
    ("柜灯", "light", "cabinet_light", "柜灯"),
    ("灯", "light", "main", "灯"),
    ("窗帘", "cover", "curtain", "窗帘"),
    ("百叶帘", "cover", "blind", "百叶帘"),
    ("遮阳帘", "cover", "shade", "遮阳帘"),
    ("空调", "climate", "ac", "空调"),
    ("温控器", "climate", "thermostat", "温控器"),
    ("热水器", "switch", "water_heater", "热水器"),
    ("插座", "switch", "socket", "插座"),
    ("空气净化器", "switch", "purifier_power", "空气净化器"),
    ("咖啡机", "switch", "coffee_machine", "咖啡机"),
    ("电饭煲", "switch", "rice_cooker", "电饭煲"),
    ("热水壶", "switch", "kettle", "热水壶"),
    ("洗衣机", "switch", "washer_power", "洗衣机"),
    ("烘干机", "switch", "dryer_power", "烘干机"),
    ("风扇", "fan", "standing_fan", "风扇"),
    ("吊扇", "fan", "ceiling_fan", "吊扇"),
    ("排风扇", "fan", "exhaust_fan", "排风扇"),
    ("电视", "media_player", "tv", "电视"),
    ("音箱", "media_player", "speaker", "音箱"),
    ("投影仪", "media_player", "projector", "投影仪"),
    ("门锁", "lock", "door_lock", "门锁"),
    ("智能门锁", "lock", "smart_lock", "智能门锁"),
    ("扫地机器人", "vacuum", "robot_vacuum", "扫地机器人"),
    ("加湿器", "humidifier", "humidifier", "加湿器"),
    ("除湿机", "dehumidifier", "dehumidifier", "除湿机"),
    ("摄像头", "camera", "indoor_cam", "摄像头"),
    ("场景", "scene", "relax_mode", "场景"),
    ("脚本", "script", "night_shutdown", "脚本"),
]

CONDITION_PHRASES = [
    ("窗帘关着", "cover", "curtain", "closed"),
    ("窗帘已经关上", "cover", "curtain", "closed"),
    ("门锁已锁", "lock", "door_lock", "locked"),
    ("灯是关的", "light", "main", "off"),
    ("空调已经打开", "climate", "ac", "on"),
]

TIME_TRIGGER_TEMPLATES = [
    "{room}每天早上7点打开{device}",
    "{room}每天晚上10点关闭{device}",
    "工作日早上7点半打开{room}{device}",
    "周末晚上9点关闭{room}{device}",
    "每天傍晚打开{room}{device}",
    "每天清晨打开{room}{device}",
    "每天睡前关闭{room}{device}",
    "每天晚上把{room}{device}调到舒适状态",
    "工作日下班后打开{room}{device}",
]

STATE_TRIGGER_TEMPLATES = [
    "{room}有人时打开{device}",
    "回家后打开{room}{device}",
    "进门后打开{room}{device}",
    "离开{room}后关闭{device}",
    "{room}检测到有人时开启{device}",
    "{room}没人后关闭{device}",
]

EVENT_TRIGGER_TEMPLATES = [
    "{room}太热时打开{device}",
    "{room}温度高于30度时启动{device}",
    "{room}湿度太高时打开{device}",
    "{room}空气太闷时启动{device}",
    "{room}漏水报警时打开{device}",
]

MULTI_ACTION_TEMPLATES = [
    "{room}有人时同时打开{device_a}和{device_b}",
    "每天晚上同时关闭{room}{device_a}和{device_b}",
    "回家后同时开启{room}{device_a}和{device_b}",
]

ROOM_DEVICE_POOL = {
    "客厅": ["主灯", "灯带", "落地灯", "窗帘", "空调", "吊扇", "电视", "音箱"],
    "主卧": ["主灯", "台灯", "夜灯", "窗帘", "空调", "加湿器"],
    "次卧": ["主灯", "台灯", "窗帘", "空调", "风扇"],
    "卧室": ["主灯", "夜灯", "窗帘", "空调", "风扇"],
    "儿童房": ["主灯", "台灯", "夜灯", "窗帘", "空调"],
    "书房": ["主灯", "书桌灯", "台灯", "窗帘", "空调", "音箱"],
    "厨房": ["主灯", "热水器", "插座", "空气净化器", "电饭煲", "热水壶", "排风扇"],
    "餐厅": ["主灯", "吊扇", "电视", "音箱"],
    "卫生间": ["主灯", "镜前灯", "热水器", "排风扇", "除湿机"],
    "主卫": ["主灯", "镜前灯", "热水器", "排风扇", "除湿机"],
    "次卫": ["主灯", "镜前灯", "热水器", "排风扇"],
    "阳台": ["主灯", "遮阳帘", "洗衣机", "烘干机"],
    "玄关": ["主灯", "夜灯", "门锁", "摄像头"],
    "走廊": ["主灯", "夜灯", "扫地机器人"],
    "储物间": ["主灯", "插座"],
    "衣帽间": ["主灯", "灯带", "除湿机"],
    "洗衣房": ["主灯", "洗衣机", "烘干机", "热水器"],
    "车库": ["主灯", "摄像头", "门锁"],
    "地下室": ["主灯", "除湿机", "摄像头"],
    "花园": ["主灯", "摄像头", "遮阳帘"],
}

INVALID_INPUT_MARKERS = (
    "周八",
    "周九",
    "25点",
    "30点",
    "同时打开和关闭",
    "又开灯又关灯",
    "打开并立刻关闭",
    "传感器",
)

OPEN_HINTS = ("打开", "开启", "启动", "执行", "开起来", "开一下", "亮一点", "调亮", "亮些")
CLOSE_HINTS = ("关闭", "关掉", "关了", "锁上", "停止", "收起", "拉上")


class HumanLikeGoldBuilder:
    """Generate a larger gold set that intentionally differs from pipeline style."""

    def __init__(self, seed: int = RANDOM_SEED) -> None:
        self.rng = random.Random(seed)
        self.registry = load_default_registry(PROJECT_ROOT)
        self.room_entities = self._build_room_entity_index()

    def _build_room_entity_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = defaultdict(list)
        room_tokens = sorted(ROOM_TOKEN_MAP.values(), key=len, reverse=True)
        for device in self.registry.devices:
            tail = device.entity_id.split(".", 1)[1]
            for room_token in room_tokens:
                prefix = f"{room_token}_"
                if tail.startswith(prefix):
                    index[room_token].append(device.entity_id)
                    break
        for room_token in index:
            index[room_token] = sorted(index[room_token])
        return dict(index)

    def build_dataset(self, target_count: int) -> list[dict[str, Any]]:
        base_inputs = self._load_case_pool()
        synthetic_inputs = self._generate_synthetic_inputs(target_count * 2)

        seen_inputs: set[str] = set()
        records: list[dict[str, Any]] = []

        for text in base_inputs + synthetic_inputs:
            if text in seen_inputs:
                continue
            seen_inputs.add(text)
            gold_dsl = self.annotate(text)
            if gold_dsl is None:
                continue
            records.append({"input_text": text, "gold_dsl": gold_dsl})
            if len(records) >= target_count:
                break

        return records

    def _load_case_pool(self) -> list[str]:
        inputs: list[str] = []
        for file_name in ("normal_cases.json", "ambiguous_cases.json"):
            path = TEST_CASE_DIR / file_name
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                continue
            for item in payload:
                if isinstance(item, dict) and isinstance(item.get("input_text"), str):
                    text = self._normalize_input(item["input_text"])
                    if text and not any(marker in text for marker in INVALID_INPUT_MARKERS):
                        inputs.append(text)
        self.rng.shuffle(inputs)
        return inputs

    def _generate_synthetic_inputs(self, target_count: int) -> list[str]:
        rooms = list(ROOM_TOKEN_MAP.keys())
        generated: set[str] = set()

        while len(generated) < target_count:
            room = self.rng.choice(rooms)
            room_devices = ROOM_DEVICE_POOL.get(room, ["主灯"])
            device_a = self.rng.choice(room_devices)
            device_b = self.rng.choice([label for label in room_devices if label != device_a] or room_devices)

            template_group = self.rng.choices(
                population=["time", "state", "event", "multi"],
                weights=[35, 30, 20, 15],
                k=1,
            )[0]

            if template_group == "time":
                template = self.rng.choice(TIME_TRIGGER_TEMPLATES)
                text = template.format(room=room, device=device_a)
            elif template_group == "state":
                template = self.rng.choice(STATE_TRIGGER_TEMPLATES)
                text = template.format(room=room, device=device_a)
            elif template_group == "event":
                template = self.rng.choice(EVENT_TRIGGER_TEMPLATES)
                text = template.format(room=room, device=device_a)
            else:
                template = self.rng.choice(MULTI_ACTION_TEMPLATES)
                text = template.format(room=room, device_a=device_a, device_b=device_b)

            if self.rng.random() < 0.18:
                cond = self.rng.choice(
                    [
                        "，并且周末执行",
                        "，并且工作日执行",
                        "，前提是窗帘关着",
                        "，而且晚上执行",
                        "，而且早上执行",
                    ]
                )
                text += cond

            generated.add(self._normalize_input(text))

        return list(generated)

    def _normalize_input(self, text: str) -> str:
        text = re.sub(r"\s+", "", text.strip())
        return text.replace("智能家居", "")

    def annotate(self, input_text: str) -> dict[str, Any] | None:
        room = self._detect_room(input_text)
        room_token = ROOM_TOKEN_MAP[room]

        trigger = self._build_trigger(input_text, room_token)
        actions = self._build_actions(input_text, room_token)
        if not actions:
            return None

        conditions = self._build_conditions(input_text, room_token, trigger)
        mode = self._select_mode(trigger, actions, input_text)
        rule_name = self._build_rule_name(room, trigger, actions, input_text)

        return {
            "rule_name": rule_name,
            "trigger": trigger,
            "conditions": conditions,
            "actions": actions,
            "mode": mode,
        }

    def _detect_room(self, text: str) -> str:
        for room in ROOM_TOKEN_MAP:
            if room in text:
                return room
        for keyword, room in ROOM_FALLBACKS.items():
            if keyword in text:
                return room
        return "客厅"

    def _build_trigger(self, text: str, room_token: str) -> dict[str, Any]:
        if any(keyword in text for keyword in ("湿度", "太潮", "潮湿")):
            return {
                "type": "event",
                "event_type": "humidity_alert",
                "event_data": {
                    "entity_id": self._find_entity(room_token, "sensor", "humidity")
                    or "sensor.bathroom_humidity",
                    "level": "high",
                },
            }
        if any(keyword in text for keyword in ("太热", "温度高", "高于30度", "闷")):
            event_type = "temperature_alert" if "闷" not in text else "air_quality_alert"
            sensor_hint = "temperature" if event_type == "temperature_alert" else "co2"
            return {
                "type": "event",
                "event_type": event_type,
                "event_data": {
                    "entity_id": self._find_entity(room_token, "sensor", sensor_hint)
                    or self._find_entity(room_token, "sensor", "temperature")
                    or "sensor.living_room_temperature",
                    "level": "high",
                },
            }
        if "漏水" in text:
            return {
                "type": "event",
                "event_type": "leak_alert",
                "event_data": {
                    "entity_id": self._find_entity(room_token, "sensor", "leak")
                    or "sensor.bathroom_leak",
                    "level": "high",
                },
            }
        if any(keyword in text for keyword in ("有人", "有动静", "检测到有人", "进门", "回家")):
            entity = (
                self._find_entity(room_token, "sensor", "motion")
                or self._find_entity(room_token, "sensor", "occupancy")
                or self._find_entity(room_token, "sensor", "door")
                or "sensor.entryway_motion"
            )
            from_state = "off"
            to_state = "on"
            if entity.endswith("_door"):
                from_state, to_state = "off", "on"
            return {
                "type": "state_change",
                "entity": entity,
                "from_state": from_state,
                "to_state": to_state,
            }
        if any(keyword in text for keyword in ("离开", "出门", "没人", "人走")):
            entity = (
                self._find_entity(room_token, "sensor", "motion")
                or self._find_entity(room_token, "sensor", "occupancy")
                or "sensor.entryway_motion"
            )
            return {
                "type": "state_change",
                "entity": entity,
                "from_state": "on",
                "to_state": "off",
            }
        return {"type": "time", "at": self._parse_time(text)}

    def _build_conditions(self, text: str, room_token: str, trigger: dict[str, Any]) -> list[dict[str, Any]]:
        conditions: list[dict[str, Any]] = []

        if "工作日" in text or "周一到周五" in text:
            conditions.append({"type": "weekday", "days": ["mon", "tue", "wed", "thu", "fri"]})
        elif "周末" in text:
            conditions.append({"type": "weekday", "days": ["sat", "sun"]})

        if trigger.get("type") != "time":
            if any(keyword in text for keyword in ("晚上", "夜间", "夜里", "睡前", "天黑")):
                conditions.append({"type": "time_range", "start": "18:00:00", "end": "23:59:59"})
            elif any(keyword in text for keyword in ("早上", "清晨", "早晨")):
                conditions.append({"type": "time_range", "start": "06:00:00", "end": "09:00:00"})
        elif any(keyword in text for keyword in ("傍晚", "晚上", "睡前", "夜间")) and self.rng.random() < 0.35:
            conditions.append({"type": "time_range", "start": "18:00:00", "end": "23:59:59"})

        for phrase, domain, hint, expected_state in CONDITION_PHRASES:
            if phrase in text:
                entity = self._find_entity(room_token, domain, hint) or self._find_entity(room_token, domain)
                if entity:
                    conditions.append(
                        {
                            "type": "state",
                            "entity": entity,
                            "expected_state": expected_state,
                        }
                    )
                break

        return conditions

    def _build_actions(self, text: str, room_token: str) -> list[dict[str, Any]]:
        target_specs = self._extract_target_specs(text)
        if not target_specs:
            target_specs = [("light", "main", "灯")]

        prefer_on = not any(keyword in text for keyword in CLOSE_HINTS)
        actions: list[dict[str, Any]] = []
        seen_entities: set[str] = set()

        for domain, hint, _label in target_specs:
            entity = self._find_entity(room_token, domain, hint) or self._find_entity(room_token, domain)
            if not entity or entity in seen_entities:
                continue
            seen_entities.add(entity)
            service = self._select_service(entity, prefer_on, text)
            data: dict[str, Any] = {}
            if entity.startswith("light.") and any(keyword in text for keyword in ("亮一点", "调亮", "亮些")):
                data = {"brightness": 180}
            actions.append({"service": service, "entity": entity, "data": data})

        climate_entity = next((action["entity"] for action in actions if action["entity"].startswith("climate.")), None)
        temperature = self._extract_temperature(text)
        if climate_entity and temperature is not None:
            actions.append(
                {
                    "service": "climate.set_temperature",
                    "entity": climate_entity,
                    "data": {"temperature": temperature},
                }
            )

        if len(actions) == 1 and self._should_add_companion_action(text):
            companion = self._companion_action(actions[0]["entity"], room_token, prefer_on)
            if companion and companion["entity"] not in seen_entities:
                actions.append(companion)

        return actions

    def _extract_target_specs(self, text: str) -> list[tuple[str, str, str]]:
        specs: list[tuple[str, str, str]] = []
        seen_labels: set[str] = set()
        has_specific_light = any(keyword in text for keyword, domain, _, _ in DEVICE_KEYWORDS if domain == "light" and keyword != "灯")

        for keyword, domain, hint, label in DEVICE_KEYWORDS:
            if keyword == "灯" and has_specific_light:
                continue
            if keyword in text and label not in seen_labels:
                specs.append((domain, hint, label))
                seen_labels.add(label)
        return specs

    def _should_add_companion_action(self, text: str) -> bool:
        return any(keyword in text for keyword in ("同时", "一起", "并且", "顺便", "和"))

    def _companion_action(self, primary_entity: str, room_token: str, prefer_on: bool) -> dict[str, Any] | None:
        domain = primary_entity.split(".", 1)[0]
        companion_domains = {
            "light": [("cover", "curtain"), ("fan", "ceiling_fan")],
            "climate": [("light", "main")],
            "media_player": [("light", "main")],
            "switch": [("light", "main")],
        }
        for target_domain, hint in companion_domains.get(domain, []):
            entity = self._find_entity(room_token, target_domain, hint) or self._find_entity(room_token, target_domain)
            if entity and entity != primary_entity:
                return {
                    "service": self._select_service(entity, prefer_on, ""),
                    "entity": entity,
                    "data": {},
                }
        return None

    def _select_mode(self, trigger: dict[str, Any], actions: list[dict[str, Any]], text: str) -> str:
        if len(actions) >= 2:
            return "queued"
        if trigger.get("type") in {"state_change", "event"}:
            return "restart"
        if any(keyword in text for keyword in ("持续", "反复", "一直")):
            return "restart"
        return "single"

    def _build_rule_name(self, room: str, trigger: dict[str, Any], actions: list[dict[str, Any]], text: str) -> str:
        first_entity = actions[0]["entity"]
        device_label = self._label_for_entity(first_entity)
        if trigger["type"] == "time":
            service = actions[0]["service"]
            verb = "开启"
            if service.endswith(("turn_off", "close_cover", "lock", "stop")):
                verb = "关闭"
            return f"{room}定时{verb}{device_label}"
        if trigger["type"] == "state_change":
            if trigger.get("to_state") == "on":
                return f"{room}感应联动{device_label}"
            return f"{room}离开后关闭{device_label}"
        event_type = trigger.get("event_type", "")
        if event_type == "humidity_alert":
            return f"{room}高湿联动{device_label}"
        if event_type == "leak_alert":
            return f"{room}漏水联动{device_label}"
        return f"{room}环境联动{device_label}"

    def _parse_time(self, text: str) -> str:
        hour_match = re.search(r"(\d{1,2})点(?:(\d{1,2})分|半)?", text)
        if hour_match:
            hour = int(hour_match.group(1))
            minute = 30 if "半" in hour_match.group(0) else int(hour_match.group(2) or 0)
            if any(keyword in text for keyword in ("晚上", "夜里", "夜间", "睡前", "傍晚")) and hour < 12:
                hour += 12
            if "中午" in text and hour < 11:
                hour += 12
            hour = max(0, min(23, hour))
            minute = max(0, min(59, minute))
            return f"{hour:02d}:{minute:02d}:00"

        if any(keyword in text for keyword in ("清晨", "早晨", "早上")):
            return "07:00:00"
        if any(keyword in text for keyword in ("傍晚", "天黑")):
            return "18:30:00"
        if any(keyword in text for keyword in ("睡前", "夜间", "夜里")):
            return "22:00:00"
        if "晚上" in text:
            return "20:00:00"
        if "中午" in text:
            return "12:00:00"
        return "20:00:00"

    def _extract_temperature(self, text: str) -> int | None:
        match = re.search(r"(\d{2})\s*度", text)
        return int(match.group(1)) if match else None

    def _label_for_entity(self, entity_id: str) -> str:
        tail = entity_id.split(".", 1)[1]
        mappings = [
            ("dehumidifier", "除湿机"),
            ("coffee_machine", "咖啡机"),
            ("rice_cooker", "电饭煲"),
            ("kettle", "热水壶"),
            ("washer_power", "洗衣机"),
            ("dryer_power", "烘干机"),
            ("curtain", "窗帘"),
            ("blind", "百叶帘"),
            ("shade", "遮阳帘"),
            ("ceiling_fan", "吊扇"),
            ("standing_fan", "风扇"),
            ("exhaust_fan", "排风扇"),
            ("ac", "空调"),
            ("thermostat", "温控器"),
            ("water_heater", "热水器"),
            ("socket", "插座"),
            ("tv", "电视"),
            ("speaker", "音箱"),
            ("projector", "投影仪"),
            ("door_lock", "门锁"),
            ("smart_lock", "智能门锁"),
            ("humidifier", "加湿器"),
            ("night_shutdown", "脚本"),
            ("relax_mode", "场景"),
            ("mirror_light", "镜前灯"),
            ("desk_lamp", "书桌灯"),
            ("floor_lamp", "落地灯"),
            ("night_light", "夜灯"),
            ("strip", "灯带"),
            ("lamp", "台灯"),
            ("main", "主灯"),
        ]
        for token, label in mappings:
            if token in tail:
                return label
        return "设备"

    def _find_entity(self, room_token: str, domain: str, hint: str | None = None) -> str | None:
        candidates = [
            entity_id
            for entity_id in self.room_entities.get(room_token, [])
            if entity_id.startswith(f"{domain}.")
        ]
        if hint:
            hinted = [entity_id for entity_id in candidates if hint in entity_id]
            if hinted:
                return hinted[0]
        return candidates[0] if candidates else None

    def _select_service(self, entity_id: str, prefer_on: bool, text: str) -> str:
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
        if domain == "climate" and self._extract_temperature(text) is not None and prefer_on:
            return "climate.turn_on"
        return on_map.get(domain, "light.turn_on") if prefer_on else off_map.get(domain, "light.turn_off")


def main() -> None:
    builder = HumanLikeGoldBuilder(seed=RANDOM_SEED)
    records = builder.build_dataset(TARGET_RECORD_COUNT)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(records)} gold records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
