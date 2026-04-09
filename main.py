from __future__ import annotations

import json
import sys

from core.pipeline import process_rule
from mock_llm_client import MockLLMClient


def print_section(title: str, content: str) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    print(content)


def main() -> None:
    user_input = "玄关有人时开灯"

    try:
        result = process_rule(user_input, MockLLMClient())

        print_section("用户输入", result["input_text"])
        print_section("DSL 草案", json.dumps(result["draft_dsl"], ensure_ascii=False, indent=2))
        print_section("修复日志", json.dumps(result["repairs"], ensure_ascii=False, indent=2))
        print_section("校验前结果", json.dumps(result["validation_before"], ensure_ascii=False, indent=2))
        print_section("修复后 DSL", json.dumps(result["repaired_dsl"], ensure_ascii=False, indent=2))
        print_section("校验后结果", json.dumps(result["validation_after"], ensure_ascii=False, indent=2))
        print_section("文本树", result["text_tree"])
        print_section("YAML", result["yaml"])
        print_section("中文解释", result["explanation"])
    except Exception as exc:
        print(f"运行失败: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
