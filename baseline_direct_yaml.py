from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class BaselineDirectYamlGenerator:
    """A deliberately brittle baseline that maps Chinese text directly to YAML."""

    def generate(self, user_input: str) -> str:
        text = user_input.strip()

        if text == "每天早上7点打开客厅窗帘":
            return (
                "alias: 早晨打开客厅窗帘\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '07:00:00'\n"
                "action:\n"
                "  - service: cover.open_cover\n"
                "    target:\n"
                "      entity_id: cover.living_room_curtain\n"
                "mode: single\n"
            )

        if text == "玄关有人时开灯":
            return (
                "alias: 玄关有人时开灯\n"
                "trigger:\n"
                "  - platform: state\n"
                "    entity_id: sensor.entryway_motion\n"
                "    to: 'on'\n"
                "action:\n"
                "  - service: light.turn_on\n"
                "    target:\n"
                "      entity_id: light.entryway_ligt\n"
            )

        if text == "离开玄关后关灯":
            return (
                "alias: 离开玄关后关灯\n"
                "trigger:\n"
                "  - platform: state\n"
                "    entity_id: sensor.entryway_motion\n"
                "    from: 'on'\n"
                "    to: 'off'\n"
                "action:\n"
                "  - service: light.turn_off\n"
                "    target:\n"
                "      entity_id: light.entryway_light\n"
                "mode: single\n"
            )

        if text == "卫生间湿度高时打开热水器":
            return (
                "alias: 湿度高时打开热水器\n"
                "trigger:\n"
                "  - platform: event\n"
                "    event_type: humidity_alert\n"
                "    event_data:\n"
                "      entity_id: sensor.bathroom_humidity\n"
                "action:\n"
                "  - service: switch.turn_on\n"
                "    target:\n"
                "      entity_id: switch.bathroom_water_heater\n"
                "condition:\n"
                "  - condition: time\n"
                "    after: '06:00:00'\n"
                "    before: '10:00:00'\n"
                "mode: single\n"
            )

        if text == "每天晚上10点关闭卧室窗帘":
            return (
                "alias 夜间关闭卧室窗帘\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '22:00:00'\n"
                "action:\n"
                "  - service: cover.close_cover\n"
                "    target:\n"
                "      entity_id: cover.bedroom_curtain\n"
                "mode: single\n"
            )

        if "厨房" in text or "阳台" in text or "车库" in text:
            return (
                "alias: 未知房间灯控\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '20:00:00'\n"
                "action:\n"
                "  - service: light.turn_on\n"
                "    target:\n"
                "      entity_id: light.kitchen_main\n"
            )

        if "传感器" in text and ("打开" in text or "关闭" in text):
            return (
                "alias: 传感器控制\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '08:00:00'\n"
                "action:\n"
                "  - service: sensor.turn_on\n"
                "    target:\n"
                "      entity_id: sensor.living_room_temperature\n"
                "mode: single\n"
            )

        if "周八" in text or "周九" in text:
            return (
                "alias: 非法星期规则\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '08:00:00'\n"
                "condition:\n"
                "  - condition: time\n"
                "    weekday: [mon, someday]\n"
                "action:\n"
                "  - service: cover.open_cover\n"
                "    target:\n"
                "      entity_id: cover.bedroom_curtain\n"
                "mode: single\n"
            )

        if "25点" in text or "三十点" in text:
            return (
                "alias: 非法时间规则\n"
                "trigger:\n"
                "  - platform: time\n"
                "    at: '25:00:00'\n"
                "action:\n"
                "  - service: light.turn_on\n"
                "    target:\n"
                "      entity_id: light.living_room_main\n"
                "mode: single\n"
            )

        if "又开灯又关灯" in text or "同时关闭和打开" in text or "打开并立刻关闭" in text:
            return (
                "alias: 冲突动作规则\n"
                "trigger:\n"
                "  - platform: state\n"
                "    entity_id: sensor.entryway_motion\n"
                "    to: 'on'\n"
                "action:\n"
                "  - service: light.turn_on\n"
                "    target:\n"
                "      entity_id: light.entryway_light\n"
                "  - service: light.turn_off\n"
                "    target:\n"
                "      entity_id: light.entryway_light\n"
                "mode: single\n"
            )

        return (
            "alias: 默认规则\n"
            "trigger:\n"
            "  - platform: time\n"
            "    at: '20:00:00'\n"
            "action:\n"
            "  - service: light.turn_on\n"
            "    target:\n"
            "      entity_id: light.living_room_main\n"
            "mode: single\n"
        )


def generate_direct_yaml(user_input: str) -> str:
    return BaselineDirectYamlGenerator().generate(user_input)


if __name__ == "__main__":
    samples = [
        "每天早上7点打开客厅窗帘",
        "玄关有人时开灯",
        "离开玄关后关灯",
        "卫生间湿度高时打开热水器",
        "每天晚上10点关闭卧室窗帘",
    ]
    generator = BaselineDirectYamlGenerator()
    for index, sample in enumerate(samples, start=1):
        print(f"=== Example {index} ===")
        print(sample)
        print(generator.generate(sample))
