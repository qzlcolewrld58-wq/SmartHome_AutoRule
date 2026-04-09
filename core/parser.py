from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.device_models import load_default_registry


DSL_PROMPT_TEMPLATE = """You are a smart-home DSL generator for Chinese user requests.

Task:
Convert the user's Chinese home automation rule description into one strict DSL JSON object.

Output constraints:
1. Output JSON only
2. Do not output markdown
3. Do not output code fences
4. Do not output explanation or notes
5. If some details are missing, fill them with conservative common smart-home defaults
6. Never invent unavailable devices
7. All entities must come from the provided entity list
8. If mode is missing, set it to "single"

DSL schema:
{{
  "rule_name": "string",
  "trigger": {{
    "type": "time | state_change | event",
    "at": "HH:MM:SS, only for time",
    "entity": "entity_id, only for state_change",
    "from_state": "string|null, optional for state_change",
    "to_state": "string|null, optional for state_change",
    "event_type": "string, only for event",
    "event_data": {{}}
  }},
  "conditions": [
    {{
      "type": "state",
      "entity": "entity_id",
      "expected_state": "string"
    }},
    {{
      "type": "time_range",
      "start": "HH:MM:SS",
      "end": "HH:MM:SS"
    }},
    {{
      "type": "weekday",
      "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }}
  ],
  "actions": [
    {{
      "service": "domain.service",
      "entity": "entity_id",
      "data": {{}}
    }}
  ],
  "mode": "single | restart | queued"
}}

Available entities:
{entity_list_block}

Completion policy:
1. "早上" -> "07:00:00"
2. "晚上" -> "20:00:00"
3. "夜间" -> "22:00:00"
4. Make service prefix match entity type
5. Do not invent devices outside the entity list

Few-shot example 1:
USER_INPUT: 每天早上7点打开客厅窗帘
JSON_OUTPUT:
{{
  "rule_name": "早晨打开客厅窗帘",
  "trigger": {{
    "type": "time",
    "at": "07:00:00"
  }},
  "conditions": [],
  "actions": [
    {{
      "service": "cover.open_cover",
      "entity": "cover.living_room_curtain",
      "data": {{}}
    }}
  ],
  "mode": "single"
}}

Few-shot example 2:
USER_INPUT: 玄关有人时开灯
JSON_OUTPUT:
{{
  "rule_name": "玄关有人时开灯",
  "trigger": {{
    "type": "state_change",
    "entity": "sensor.entryway_motion",
    "from_state": "off",
    "to_state": "on"
  }},
  "conditions": [],
  "actions": [
    {{
      "service": "light.turn_on",
      "entity": "light.entryway_main",
      "data": {{}}
    }}
  ],
  "mode": "single"
}}

Now output JSON for the following user request only.
USER_INPUT: {user_input}
"""


class ParserOutputError(ValueError):
    def __init__(self, message: str, telemetry: dict[str, Any]) -> None:
        super().__init__(message)
        self.telemetry = telemetry


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Return raw model output for the prompt."""


def build_prompt(user_input: str, entity_list: list[str]) -> str:
    entity_list_block = "\n".join(f"- {entity}" for entity in entity_list)
    return DSL_PROMPT_TEMPLATE.format(
        entity_list_block=entity_list_block,
        user_input=user_input.strip(),
    )


def parse_rule_text(user_input: str, entity_list: list[str], llm_client: LLMClient) -> dict[str, Any]:
    payload, _ = parse_rule_text_with_meta(user_input, entity_list, llm_client)
    return payload


def parse_rule_text_with_meta(
    user_input: str,
    entity_list: list[str],
    llm_client: LLMClient,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = build_prompt(user_input, entity_list)
    telemetry: dict[str, Any] = {
        "json_extract_success": False,
        "first_attempt_success": False,
        "retry_used": False,
        "json_extract_method": "",
        "prompt_length": len(prompt),
        "raw_output_length": 0,
    }

    raw_output = llm_client.generate(prompt)
    telemetry["raw_output_length"] = len(raw_output)

    try:
        payload, method = _extract_and_parse_json(raw_output)
        telemetry["json_extract_success"] = True
        telemetry["first_attempt_success"] = True
        telemetry["json_extract_method"] = method
        return payload, telemetry
    except ValueError:
        telemetry["retry_used"] = True

    retry_prompt = prompt + "\n\nRetry instruction: output exactly one valid JSON object and nothing else."
    retry_output = llm_client.generate(retry_prompt)
    telemetry["raw_output_length"] = len(retry_output)

    try:
        payload, method = _extract_and_parse_json(retry_output)
        telemetry["json_extract_success"] = True
        telemetry["json_extract_method"] = method
        return payload, telemetry
    except ValueError as exc:
        raise ParserOutputError(str(exc), telemetry) from exc


def _extract_and_parse_json(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped), "direct"

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1)), "fenced"

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(stripped[start : end + 1]), "substring"

    raise ValueError("No valid JSON object found in LLM output.")


if __name__ == "__main__":
    from mock_llm_client import MockLLMClient

    registry = load_default_registry(PROJECT_ROOT)
    entity_list = registry.get_all_entity_ids()
    client = MockLLMClient()
    result, telemetry = parse_rule_text_with_meta("每天早上7点打开客厅窗帘", entity_list, client)
    print(json.dumps({"result": result, "telemetry": telemetry}, ensure_ascii=False, indent=2))
