from __future__ import annotations

import json
from pathlib import Path

from core.repairer import DSLRepairer
from core.validator import DSLValidator


def main() -> None:
    project_root = Path(__file__).resolve().parent
    _ = project_root

    broken_payload = {
        "rule_name": "玄关夜间有人时开灯",
        "trigger": {
            "type": "state_change",
            "entity": "sensor.entryway_motin",
            "from_state": "off",
            "to_state": "on",
        },
        "conditions": [
            {
                "type": "state",
                "entity": "light.entryway_ligt",
                "expected_state": "off",
            }
        ],
        "actions": [
            {
                "service": "switch.turn_on",
                "entity": "light.entryway_ligt",
                "data": {"brightness": 180},
            }
        ]
    }

    validator = DSLValidator()
    repairer = DSLRepairer()

    first_validation = validator.validate_payload(broken_payload)
    repair_result = repairer.repair_payload(broken_payload)
    second_validation = validator.validate_payload(repair_result.repaired_payload)

    print("原始 DSL:")
    print(json.dumps(broken_payload, ensure_ascii=False, indent=2))
    print()

    print("第一次校验结果:")
    print(first_validation.model_dump_json(indent=2, ensure_ascii=False))
    print()

    print("修复日志:")
    print(json.dumps([log.model_dump() for log in repair_result.repair_logs], ensure_ascii=False, indent=2))
    print()

    print("修复后 DSL:")
    print(json.dumps(repair_result.repaired_payload, ensure_ascii=False, indent=2))
    print()

    print("第二次校验结果:")
    print(second_validation.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
