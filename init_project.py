from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_DIRS = [
    "data",
    "models",
    "core",
    "tests",
    "outputs",
]


PROJECT_FILES = [
    "models/__init__.py",
    "models/dsl_models.py",
    "models/device_models.py",
    "core/__init__.py",
    "core/parser.py",
    "core/validator.py",
    "core/repairer.py",
    "core/yaml_converter.py",
    "core/explainer.py",
    "core/pipeline.py",
    "tests/__init__.py",
    "tests/test_smoke.py",
]


REQUIREMENTS_TEXT = "\n".join(
    [
        "pydantic>=2.7,<3.0",
        "PyYAML>=6.0,<7.0",
        "rapidfuzz>=3.9,<4.0",
        "",
    ]
)


DEVICES_EXAMPLE = [
    {
        "entity_id": "sensor.living_room_temperature",
        "name": "\u5ba2\u5385\u6e29\u5ea6\u4f20\u611f\u5668",
        "room": "\u5ba2\u5385",
        "domain": "sensor",
        "supported_actions": [],
    },
    {
        "entity_id": "climate.living_room_ac",
        "name": "\u5ba2\u5385\u7a7a\u8c03",
        "room": "\u5ba2\u5385",
        "domain": "climate",
        "supported_actions": ["turn_on", "turn_off", "set_temperature"],
    },
]


GOLD_DSL_EXAMPLE = {
    "name": "\u89c4\u5219_\u5ba2\u5385\u9ad8\u6e29\u5f00\u7a7a\u8c03",
    "source_text": "\u5982\u679c\u5ba2\u5385\u6e29\u5ea6\u9ad8\u4e8e30\u5ea6\uff0c\u5c31\u6253\u5f00\u5ba2\u5385\u7a7a\u8c03",
    "trigger": {
        "type": "numeric_state",
        "entity_id": "sensor.living_room_temperature",
        "operator": ">",
        "threshold": 30,
    },
    "conditions": [],
    "actions": [
        {
            "service": "homeassistant.turn_on",
            "target_entity_id": "climate.living_room_ac",
            "data": {},
        }
    ],
}


MAIN_TEXT = (
    "def main() -> None:\n"
    '    print("project initialized successfully")\n'
    "\n"
    '\nif __name__ == "__main__":\n'
    "    main()\n"
)


def ensure_directories(project_root: Path) -> None:
    for relative_dir in PROJECT_DIRS:
        (project_root / relative_dir).mkdir(parents=True, exist_ok=True)


def ensure_empty_files(project_root: Path) -> None:
    for relative_file in PROJECT_FILES:
        file_path = project_root / relative_file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch(exist_ok=True)


def write_text_file(file_path: Path, content: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def write_json_file(file_path: Path, content: Any) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def initialize_project(project_root: Path) -> None:
    ensure_directories(project_root)
    ensure_empty_files(project_root)

    write_text_file(project_root / "requirements.txt", REQUIREMENTS_TEXT)
    write_json_file(project_root / "data" / "devices.json", DEVICES_EXAMPLE)
    write_json_file(project_root / "data" / "gold_dsl.json", GOLD_DSL_EXAMPLE)
    write_text_file(project_root / "main.py", MAIN_TEXT)


def main() -> None:
    project_root = Path(__file__).resolve().parent
    initialize_project(project_root)
    print("project initialized successfully")


if __name__ == "__main__":
    main()
