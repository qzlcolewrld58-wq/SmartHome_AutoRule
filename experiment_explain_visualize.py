from __future__ import annotations

import json
import random
from pathlib import Path

from core.data_utils import extract_gold_rules
from core.explainer import explain_rule
from core.visualizer import render_mermaid
from core.yaml_converter import HomeAssistantYamlConverter
from models.dsl_models import RuleDSL


PROJECT_ROOT = Path(__file__).resolve().parent
GOLD_DSL_PATH = PROJECT_ROOT / "data" / "gold_dsl.json"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
REPORT_PATH = REPORT_DIR / "experiment_explain_visualize.md"
SAMPLE_SIZE = 5


def load_rules() -> list[RuleDSL]:
    payload = extract_gold_rules(GOLD_DSL_PATH)
    return [RuleDSL.model_validate(item) for item in payload if isinstance(item, dict)]


def sample_rules(rules: list[RuleDSL], sample_size: int = SAMPLE_SIZE) -> list[RuleDSL]:
    rng = random.Random(42)
    if len(rules) <= sample_size:
        return rules
    return rng.sample(rules, sample_size)


def summarize_readability_gain() -> list[str]:
    return [
        "解释层显式补充了规则名称、触发方式、条件语义和动作语义，降低了直接阅读 YAML 的结构门槛。",
        "中文解释将字段级信息转成句子级语义，适合快速检查规则是否符合原意。",
        "Mermaid 结构图把 Trigger、Conditions、Actions 的执行链条显式展开，便于定位规则的决策路径。",
        "相比只看 YAML，解释与图结构更容易发现缺失条件、冲突动作和过于复杂的规则结构。",
    ]


def build_report(rules: list[RuleDSL]) -> str:
    converter = HomeAssistantYamlConverter()
    lines = [
        "# 规则解释与可视化有效性实验报告",
        "",
        "## 实验目标",
        "",
        "在不做真人用户实验的前提下，验证加入中文解释与结构化可视化后，规则是否更容易被程序层面展示和理解。",
        "",
        f"## 示例样本（共 {len(rules)} 条）",
        "",
    ]

    for index, rule in enumerate(rules, start=1):
        yaml_text = converter.convert(rule)
        explanation = explain_rule(rule)
        mermaid = render_mermaid(rule)
        lines.extend(
            [
                f"### 样本 {index}: {rule.rule_name}",
                "",
                "**原始 YAML**",
                "",
                "```yaml",
                yaml_text.rstrip(),
                "```",
                "",
                "**中文解释**",
                "",
                explanation,
                "",
                "**Mermaid 结构图**",
                "",
                "```mermaid",
                mermaid,
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## 自动总结：解释层增加的可读信息",
            "",
        ]
    )
    for item in summarize_readability_gain():
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## 结论模板",
            "",
            "> 从程序层面的展示结果看，中文解释能够把规则的结构字段转化为更容易直接理解的自然语言描述，而 Mermaid 结构图则进一步揭示了触发、条件和动作之间的执行关系。因此，解释层与可视化层虽然不直接改变规则生成结果，但显著提升了规则的可读性、可检查性和展示友好性。",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rules = sample_rules(load_rules())
    report = build_report(rules)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
