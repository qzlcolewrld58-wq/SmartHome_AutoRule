from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEVICE_PATH = PROJECT_ROOT / "data" / "devices.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "test_cases"
TARGET_COUNTS = {
    "normal": 2000,
    "ambiguous": 1500,
    "error_conflict": 1500,
}


DEVICE_NAME_MAP = {
    "main": "主灯",
    "lamp": "台灯",
    "ceiling": "吸顶灯",
    "wall": "壁灯",
    "strip": "灯带",
    "floor_lamp": "落地灯",
    "desk_lamp": "书桌灯",
    "mirror_light": "镜前灯",
    "cabinet_light": "柜灯",
    "night_light": "夜灯",
    "bedside_left": "左床头灯",
    "bedside_right": "右床头灯",
    "ac": "空调",
    "thermostat": "温控器",
    "water_heater": "热水器",
    "socket": "插座",
    "purifier_power": "空气净化器电源",
    "kettle": "热水壶",
    "coffee_machine": "咖啡机",
    "rice_cooker": "电饭煲",
    "dryer_power": "烘干机电源",
    "washer_power": "洗衣机电源",
    "motion": "人体传感器",
    "temperature": "温度传感器",
    "humidity": "湿度传感器",
    "door": "门磁",
    "window": "窗磁",
    "illuminance": "光照传感器",
    "smoke": "烟雾传感器",
    "co2": "二氧化碳传感器",
    "leak": "漏水传感器",
    "occupancy": "在位传感器",
    "curtain": "窗帘",
    "blind": "百叶帘",
    "shade": "遮阳帘",
    "ceiling_fan": "吊扇",
    "standing_fan": "落地风扇",
    "exhaust_fan": "排风扇",
    "tv": "电视",
    "speaker": "音箱",
    "projector": "投影仪",
    "door_lock": "门锁",
    "smart_lock": "智能门锁",
    "garage_lock": "车库门锁",
    "robot_vacuum": "扫地机器人",
    "humidifier": "加湿器",
    "dehumidifier": "除湿机",
    "indoor_cam": "室内摄像头",
    "outdoor_cam": "室外摄像头",
    "doorbell_cam": "门铃摄像头",
    "garage_cam": "车库摄像头",
    "garden_cam": "花园摄像头",
    "alarm_siren": "警报器",
    "movie_mode": "观影模式",
    "sleep_mode": "睡眠模式",
    "away_mode": "离家模式",
    "reading_mode": "阅读模式",
    "dinner_mode": "晚餐模式",
    "relax_mode": "放松模式",
    "morning_routine": "晨间脚本",
    "night_shutdown": "夜间关闭脚本",
    "leave_home": "离家脚本",
    "arrive_home": "回家脚本",
    "sleep_prep": "睡前准备脚本",
    "kitchen_cleanup": "厨房清理脚本",
}


def load_devices() -> list[dict]:
    return json.loads(DEVICE_PATH.read_text(encoding="utf-8"))


def normalize_device_suffix(entity_id: str) -> str:
    suffix = entity_id.split(".", 1)[1]
    parts = suffix.split("_")
    if len(parts) >= 3:
        candidates = [
            "_".join(parts[-3:]),
            "_".join(parts[-2:]),
            parts[-1],
        ]
    elif len(parts) == 2:
        candidates = ["_".join(parts[-2:]), parts[-1]]
    else:
        candidates = [parts[-1]]

    for candidate in candidates:
        cleaned = re.sub(r"_\d+$", "", candidate)
        if cleaned in DEVICE_NAME_MAP:
            return cleaned

    return re.sub(r"_\d+$", "", parts[-1])


def device_label(device: dict) -> str:
    key = normalize_device_suffix(device["entity_id"])
    return DEVICE_NAME_MAP.get(key, DEVICE_NAME_MAP.get(device["type"], key))


def build_seed_normal_cases() -> list[dict]:
    cases = [
        "每天早上7点打开客厅窗帘",
        "每天晚上10点关闭卧室窗帘",
        "玄关有人时开灯",
        "离开玄关后关灯",
        "卫生间湿度高时打开热水器",
        "每天晚上八点打开客厅主灯",
        "每天早上六点半关闭卧室空调",
        "工作日早上七点打开客厅窗帘",
        "周末晚上十点关闭客厅主灯",
        "每天晚上九点打开卧室主灯",
        "每天早上八点关闭热水器",
        "每天傍晚六点打开玄关灯",
        "每天晚上十一点关闭玄关灯",
        "卧室温度高时打开卧室空调",
        "客厅温度高时打开客厅空调",
        "每天下午五点关闭客厅窗帘",
        "每天上午九点打开玄关香薰",
        "每天晚上十点关闭玄关香薰",
        "每天中午十二点关闭客厅主灯",
        "每天凌晨一点关闭卧室主灯",
        "每天清晨六点打开卧室窗帘",
        "每天晚上七点半打开客厅空调",
        "每天晚上九点半关闭客厅空调",
        "周一早上七点打开客厅窗帘",
        "周五晚上十点关闭卧室窗帘",
        "每天晚上八点打开卧室空调",
        "每天早上七点关闭卧室空调",
        "每天晚上六点打开客厅主灯",
        "每天晚上十点关闭客厅窗帘",
        "每天早上八点打开玄关灯",
    ]
    return [_case(text, "normal", "easy") for text in cases]


def build_seed_ambiguous_cases() -> list[dict]:
    cases = [
        "晚上回家时把灯打开",
        "早上帮我把窗帘拉开",
        "太热了就开空调",
        "洗澡前把热水器打开",
        "出门后记得关灯",
        "天黑后开玄关灯",
        "睡觉前把卧室灯关掉",
        "周末早上打开窗帘",
        "有人来时玄关亮一点",
        "空气潮的时候开热水器",
        "夜里把客厅灯关了",
        "傍晚的时候开客厅灯",
        "回卧室前先开空调",
        "早起时打开卧室窗帘",
        "离开卫生间后别忘了关热水器",
        "晚上热了就把卧室空调开起来",
        "玄关有动静时开灯",
        "客厅闷的时候开空调",
        "卧室太亮时把窗帘拉上",
        "白天别开灯",
        "周一到周五早上把窗帘打开",
        "洗漱完关掉热水器",
        "晚饭后开客厅灯",
        "半夜别让卧室灯亮着",
        "进门的时候亮玄关灯",
        "晚上睡前关客厅窗帘",
        "早晨让卧室亮一点",
        "天气热的时候开客厅空调",
        "周末晚上客厅灯别太亮",
        "人走了把玄关那边都关掉",
    ]
    return [_case(text, "ambiguous", "medium") for text in cases]


def build_seed_error_cases() -> list[dict]:
    cases = [
        "每天早上7点打开厨房灯",
        "把客厅电视打开",
        "卫生间有人时打开卫生间传感器",
        "每天25点打开客厅灯",
        "玄关没人时又开灯又关灯",
        "把卧室风扇打开",
        "周八晚上关闭卧室窗帘",
        "晚上打开阳台灯",
        "客厅窗帘打开并立刻关闭",
        "把玄关门锁打开",
        "每天早上七点打开客厅温度传感器",
        "卧室湿度高时打开卧室除湿机",
        "如果厨房有人就开厨房灯",
        "每天早上打开客厅和厨房所有灯",
        "把热水器调到四十度并关闭",
        "凌晨三十点关闭卧室主灯",
        "周末周九打开客厅窗帘",
        "玄关有人时打开light.entryway",
        "打开不存在的设备",
        "客厅太热时关闭并打开客厅空调",
        "把卧室窗帘升高",
        "每天早上七点打开车库灯",
        "卫生间湿度高时关闭并打开热水器",
        "早上六点打开主卧灯",
        "离开玄关后打开传感器",
        "把客厅灯切到阅读模式",
        "晚上十点把玄关香薰和电视都关掉",
        "周一周二周八打开卧室窗帘",
        "每天8点把未知灯打开",
        "有人时同时关闭和打开客厅窗帘",
    ]
    return [_case(text, "error_conflict", "hard") for text in cases]


def controllable_devices(devices: list[dict]) -> list[dict]:
    return [device for device in devices if device["supported_services"]]


def sensor_devices(devices: list[dict]) -> list[dict]:
    return [device for device in devices if device["type"] == "sensor"]


def build_auto_normal_cases(devices: list[dict], target_count: int) -> list[dict]:
    cases: list[dict] = []
    time_templates = [
        "每天早上7点打开{room}{device}",
        "每天晚上10点关闭{room}{device}",
        "工作日晚上8点打开{room}{device}",
        "每天早上6点半关闭{room}{device}",
    ]
    action_map = {
        "light": ("打开", "关闭"),
        "climate": ("打开", "关闭"),
        "switch": ("打开", "关闭"),
        "cover": ("打开", "关闭"),
        "fan": ("打开", "关闭"),
        "media_player": ("打开", "关闭"),
        "lock": ("锁上", "解锁"),
        "vacuum": ("启动", "停止"),
        "humidifier": ("打开", "关闭"),
        "dehumidifier": ("打开", "关闭"),
        "scene": ("开启", "开启"),
        "script": ("执行", "执行"),
        "siren": ("打开", "关闭"),
    }

    devices_pool = controllable_devices(devices)
    index = 0
    while len(cases) < target_count:
        device = devices_pool[index % len(devices_pool)]
        room = device["room"]
        label = device_label(device)
        open_word, close_word = action_map.get(device["type"], ("打开", "关闭"))
        template = time_templates[index % len(time_templates)]
        if "关闭" in template:
            text = template.format(room=room, device=label).replace("关闭", close_word, 1)
        else:
            text = template.format(room=room, device=label).replace("打开", open_word, 1)
        cases.append(_case(text, "normal", "easy"))
        index += 1
    return cases


def build_auto_ambiguous_cases(devices: list[dict], target_count: int) -> list[dict]:
    cases: list[dict] = []
    templates = [
        "{room}太热了就把{device}开起来",
        "晚上帮我把{room}{device}关掉",
        "回家后把{room}{device}打开",
        "天黑以后让{room}{device}亮一点",
        "{room}有动静时把{device}开一下",
        "睡前把{room}{device}关了",
    ]
    pool = controllable_devices(devices)
    index = 0
    while len(cases) < target_count:
        device = pool[index % len(pool)]
        text = templates[index % len(templates)].format(
            room=device["room"],
            device=device_label(device),
        )
        cases.append(_case(text, "ambiguous", "medium"))
        index += 1
    return cases


def build_auto_error_cases(devices: list[dict], target_count: int) -> list[dict]:
    cases: list[dict] = []
    controllable = controllable_devices(devices)
    sensors = sensor_devices(devices)
    error_templates: list[str] = []

    for device in controllable[: max(1, len(controllable))]:
        room = device["room"]
        label = device_label(device)
        error_templates.extend(
            [
                f"每天25点打开{room}{label}",
                f"周八晚上关闭{room}{label}",
                f"同时打开和关闭{room}{label}",
            ]
        )
        if len(error_templates) >= target_count * 2:
            break

    for sensor in sensors[: max(1, len(sensors))]:
        error_templates.append(f"打开{sensor['room']}{device_label(sensor)}")
        if len(error_templates) >= target_count * 3:
            break

    index = 0
    while len(cases) < target_count:
        text = error_templates[index % len(error_templates)]
        cases.append(_case(text, "error_conflict", "hard"))
        index += 1
    return cases


def _case(input_text: str, category: str, expected_difficulty: str) -> dict:
    return {
        "input_text": input_text,
        "category": category,
        "expected_difficulty": expected_difficulty,
    }


def write_cases(file_name: str, cases: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / file_name
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    devices = load_devices()

    normal_cases = build_seed_normal_cases()
    ambiguous_cases = build_seed_ambiguous_cases()
    error_cases = build_seed_error_cases()

    normal_cases.extend(build_auto_normal_cases(devices, TARGET_COUNTS["normal"] - len(normal_cases)))
    ambiguous_cases.extend(build_auto_ambiguous_cases(devices, TARGET_COUNTS["ambiguous"] - len(ambiguous_cases)))
    error_cases.extend(build_auto_error_cases(devices, TARGET_COUNTS["error_conflict"] - len(error_cases)))

    write_cases("normal_cases.json", normal_cases)
    write_cases("ambiguous_cases.json", ambiguous_cases)
    write_cases("error_conflict_cases.json", error_cases)

    print(f"Generated {len(normal_cases)} normal cases")
    print(f"Generated {len(ambiguous_cases)} ambiguous cases")
    print(f"Generated {len(error_cases)} error/conflict cases")
    print(f"Total cases: {len(normal_cases) + len(ambiguous_cases) + len(error_cases)}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
