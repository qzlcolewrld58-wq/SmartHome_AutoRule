from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, PathPatch, Polygon, Rectangle

from core.pipeline import process_rule
from llm_client_factory import get_default_llm_client
from mock_llm_client import MockLLMClient


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"

COMPARISON_REPORT_PATH = REPORT_DIR / "comparison_report.md"
REPAIR_REPORT_PATH = REPORT_DIR / "experiment_repair_effectiveness.md"
STRUCTURED_REPORT_PATH = REPORT_DIR / "structured_accuracy_report.md"
BATCH_RESULTS_PATH = REPORT_DIR / "batch_results.json"

CASE_SPECS = [
    (
        "case_01_bilingual_entryway_light",
        "Entryway Light Control",
        "玄关有人时开灯",
        "When someone is detected in the entryway, turn on the entryway light.",
    ),
    (
        "case_02_bilingual_bedroom_ac",
        "Bedroom Air Conditioner",
        "卧室太热时打开空调",
        "When the bedroom is too hot, turn on the air conditioner.",
    ),
    (
        "case_03_bilingual_living_room_curtain",
        "Living Room Curtain",
        "每天早上7点打开客厅窗帘",
        "Open the living room curtain at 7:00 every morning.",
    ),
    (
        "case_04_bilingual_bathroom_water_heater",
        "Bathroom Water Heater",
        "卫生间湿度高时打开热水器",
        "Turn on the bathroom water heater when humidity is high.",
    ),
    (
        "case_05_bilingual_study_fan",
        "Study Fan Control",
        "书房有人时打开风扇",
        "Turn on the fan when motion is detected in the study.",
    ),
]


def configure_style() -> None:
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["savefig.facecolor"] = "white"
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.titlesize"] = 15
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_percent(report_text: str, label: str) -> float:
    pattern = rf"{re.escape(label)}\s*[:|]\s*([0-9.]+)%"
    match = re.search(pattern, report_text)
    if not match:
        raise ValueError(f"Unable to locate percentage for label: {label}")
    return float(match.group(1))


def extract_decimal(report_text: str, label: str) -> float:
    pattern = rf"{re.escape(label)}\s*[:|]\s*([0-9.]+)"
    match = re.search(pattern, report_text)
    if not match:
        raise ValueError(f"Unable to locate decimal for label: {label}")
    return float(match.group(1))


def parse_comparison_metrics() -> dict[str, dict[str, float]]:
    text = read_text(COMPARISON_REPORT_PATH)
    rows = {}
    for metric in (
        "Rule Completeness Rate",
        "Validation Pass Rate",
        "End-to-End Executable Rate",
    ):
        pattern = rf"\|\s*{re.escape(metric)}\s*\|\s*([0-9.]+)%\s*\|\s*([0-9.]+)%\s*\|"
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Unable to parse comparison metric row: {metric}")
        rows[metric] = {
            "Direct YAML": float(match.group(1)),
            "DSL Middle Layer": float(match.group(2)),
        }
    return rows


def parse_repair_summary() -> dict[str, float]:
    text = read_text(REPAIR_REPORT_PATH)
    try:
        return {
            "Before Repair Pass Rate": extract_percent(text, "Before Repair Pass Rate"),
            "After Repair Pass Rate": extract_percent(text, "After Repair Pass Rate"),
            "Repair Gain": extract_percent(text, "Repair Gain"),
        }
    except ValueError:
        percentages = re.findall(r"([0-9.]+)%", text)
        if len(percentages) < 3:
            raise
        return {
            "Before Repair Pass Rate": float(percentages[0]),
            "After Repair Pass Rate": float(percentages[1]),
            "Repair Gain": float(percentages[2]),
        }


def parse_repair_error_table() -> list[dict[str, Any]]:
    text = read_text(REPAIR_REPORT_PATH)
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"\|\s*([a-z_]+)\s*\|\s*(\d+)\s*\|\s*([0-9.]+)%\s*\|")
    for error_type, sample_count, success_rate in pattern.findall(text):
        rows.append(
            {
                "error_type": error_type,
                "sample_count": int(sample_count),
                "success_rate": float(success_rate),
            }
        )
    if not rows:
        raise ValueError("Unable to parse repair error table.")
    rows.sort(key=lambda item: item["success_rate"], reverse=True)
    return rows


def parse_structured_metrics() -> dict[str, float]:
    text = read_text(STRUCTURED_REPORT_PATH)
    return {
        "Field Accuracy": extract_decimal(text, "Field Accuracy"),
        "Trigger Type F1": extract_decimal(text, "Trigger Type F1"),
        "Entity Selection Micro-F1": extract_decimal(text, "Entity Selection Micro-F1"),
    }


def load_batch_results() -> dict[str, Any]:
    return json.loads(BATCH_RESULTS_PATH.read_text(encoding="utf-8"))


def compute_category_metrics(batch_payload: dict[str, Any]) -> list[dict[str, float | str]]:
    results = batch_payload["results"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(item["category"], []).append(item)

    category_rows: list[dict[str, float | str]] = []
    for category in ("normal", "ambiguous", "error_conflict"):
        items = grouped.get(category, [])
        total = len(items)
        if total == 0:
            continue
        before = sum(1 for item in items if item["validation_passed_before"]) / total * 100
        after = sum(1 for item in items if item["validation_passed_after"]) / total * 100
        category_rows.append(
            {
                "category": category,
                "before": before,
                "after": after,
                "gain": after - before,
            }
        )
    return category_rows


def add_bar_labels(ax: plt.Axes, fmt: str = "{:.2f}%", padding: float = 1.5) -> None:
    for patch in ax.patches:
        height = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            height + padding,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=10,
            color="#1f2937",
        )


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure: {path}")


def plot_dsl_vs_direct_yaml(metrics: dict[str, dict[str, float]], output_path: Path) -> None:
    labels = list(metrics.keys())
    direct_values = [metrics[label]["Direct YAML"] for label in labels]
    dsl_values = [metrics[label]["DSL Middle Layer"] for label in labels]
    x = np.arange(len(labels))
    width = 0.34

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(x - width / 2, direct_values, width, label="Direct YAML", color="#8fa8c8")
    ax.bar(x + width / 2, dsl_values, width, label="DSL Middle Layer", color="#284b63")
    add_bar_labels(ax)
    ax.set_title("DSL vs Direct YAML: Core Engineering Metrics")
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 110)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(frameon=False)
    save_figure(fig, output_path)


def plot_repair_before_after(summary: dict[str, float], output_path: Path) -> None:
    labels = ["Before Repair", "After Repair"]
    values = [summary["Before Repair Pass Rate"], summary["After Repair Pass Rate"]]
    colors = ["#9aa5b1", "#2d6a4f"]

    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    bars = ax.bar(labels, values, color=colors, width=0.55)
    add_bar_labels(ax)
    ax.set_title("Impact of Validation and Automatic Repair")
    ax.set_ylabel("Pass Rate (%)")
    ax.set_ylim(0, 110)
    ax.text(
        0.5,
        104,
        f"Repair Gain = {summary['Repair Gain']:.2f}%",
        ha="center",
        va="center",
        fontsize=11,
        color="#1f2937",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#eef2f7", "edgecolor": "#cbd5e1"},
    )
    for bar in bars:
        bar.set_edgecolor("white")
    save_figure(fig, output_path)


def plot_repair_error_types(rows: list[dict[str, Any]], output_path: Path) -> None:
    labels = [item["error_type"] for item in rows]
    values = [item["success_rate"] for item in rows]
    palette = sns.light_palette("#355070", n_colors=len(labels), reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6.8))
    ax.barh(labels, values, color=palette, edgecolor="none")
    ax.set_title("Repair Success Rate by Error Type")
    ax.set_xlabel("Repair Success Rate (%)")
    ax.set_xlim(0, 110)
    ax.invert_yaxis()
    for index, value in enumerate(values):
        ax.text(value + 1.5, index, f"{value:.2f}%", va="center", fontsize=10, color="#1f2937")
    save_figure(fig, output_path)


def plot_category_robustness(rows: list[dict[str, float | str]], output_path: Path) -> None:
    categories = [str(item["category"]) for item in rows]
    before = [float(item["before"]) for item in rows]
    after = [float(item["after"]) for item in rows]
    gain = [float(item["gain"]) for item in rows]
    x = np.arange(len(categories))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(x - width, before, width, label="Before Repair", color="#9aa5b1")
    ax.bar(x, after, width, label="After Repair", color="#2d6a4f")
    ax.bar(x + width, gain, width, label="Repair Gain", color="#577590")
    add_bar_labels(ax)
    ax.set_title("Robustness Across Input Categories")
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 110)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(frameon=False)
    save_figure(fig, output_path)


def plot_structured_ml_metrics(metrics: dict[str, float], output_path: Path) -> None:
    labels = list(metrics.keys())
    values = list(metrics.values())

    fig, ax = plt.subplots(figsize=(9, 5.6))
    bars = ax.bar(labels, values, color=["#577590", "#355070", "#2f3e46"], width=0.6)
    ax.set_title("Structured Prediction Quality")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#1f2937",
        )
    save_figure(fig, output_path)


def wrap_text(text: str, width: int, max_lines: int) -> str:
    wrapped = textwrap.fill(text.strip(), width=width, break_long_words=False, break_on_hyphens=False)
    lines = wrapped.splitlines()
    if len(lines) <= max_lines:
        return wrapped
    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1].rstrip() + " ..."
    return "\n".join(clipped)


def format_json_block(payload: dict[str, Any], max_chars: int = 900) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 4].rstrip() + "\n..."


def format_text_block(text: str, width: int, max_lines: int) -> str:
    lines = text.strip().splitlines()
    normalized = "\n".join(line.rstrip() for line in lines)
    return wrap_text(normalized, width=width, max_lines=max_lines)


def draw_panel(ax: plt.Axes, title: str, body: str, *, monospaced: bool = False, icon_kind: str | None = None) -> None:
    ax.set_axis_off()
    panel = FancyBboxPatch(
        (0.01, 0.01),
        0.98,
        0.98,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=0.9,
        edgecolor="#cbd5e1",
        facecolor="#f8fafc",
        transform=ax.transAxes,
    )
    ax.add_patch(panel)
    title_x = 0.04
    if icon_kind is not None:
        draw_icon(ax, icon_kind, 0.04, 0.89, size=0.07)
        title_x = 0.15
    ax.text(title_x, 0.93, title, fontsize=12, fontweight="bold", color="#1f2937", va="top", transform=ax.transAxes)
    ax.text(
        0.04,
        0.86,
        body,
        fontsize=9.5,
        color="#111827",
        va="top",
        ha="left",
        family="DejaVu Sans Mono" if monospaced and not contains_cjk(body) else "Microsoft YaHei",
        transform=ax.transAxes,
    )


def draw_icon(ax: plt.Axes, kind: str, x: float, y: float, size: float = 0.06) -> None:
    color = "#52796f"
    secondary = "#84a98c"
    lw = 1.2

    if kind == "house":
        roof = Polygon(
            [(x, y + size * 0.6), (x + size * 0.5, y + size), (x + size, y + size * 0.6)],
            closed=False,
            fill=False,
            edgecolor=color,
            linewidth=lw,
            transform=ax.transAxes,
        )
        body = Rectangle(
            (x + size * 0.15, y),
            size * 0.7,
            size * 0.6,
            fill=False,
            edgecolor=color,
            linewidth=lw,
            transform=ax.transAxes,
        )
        door = Rectangle(
            (x + size * 0.42, y),
            size * 0.16,
            size * 0.28,
            fill=False,
            edgecolor=secondary,
            linewidth=lw,
            transform=ax.transAxes,
        )
        ax.add_patch(roof)
        ax.add_patch(body)
        ax.add_patch(door)
        return

    if kind == "sensor":
        center = (x + size * 0.5, y + size * 0.45)
        ax.add_patch(Circle(center, size * 0.12, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        ax.add_patch(Arc(center, size * 0.65, size * 0.65, theta1=310, theta2=50, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        ax.add_patch(Arc(center, size * 0.95, size * 0.95, theta1=320, theta2=40, edgecolor=secondary, linewidth=lw, transform=ax.transAxes))
        return

    if kind == "light":
        bulb = Circle((x + size * 0.5, y + size * 0.62), size * 0.24, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes)
        base = Rectangle((x + size * 0.38, y + size * 0.22), size * 0.24, size * 0.15, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes)
        ax.add_patch(bulb)
        ax.add_patch(base)
        for dx, dy in ((0.5, 1.0), (0.15, 0.82), (0.85, 0.82)):
            ax.plot(
                [x + size * dx, x + size * dx],
                [y + size * (dy - 0.08), y + size * dy],
                color=secondary,
                linewidth=lw,
                transform=ax.transAxes,
            )
        return

    if kind == "dsl":
        ax.add_patch(
            FancyBboxPatch(
                (x + size * 0.1, y + size * 0.08),
                size * 0.8,
                size * 0.84,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                fill=False,
                edgecolor=color,
                linewidth=lw,
                transform=ax.transAxes,
            )
        )
        for i in range(3):
            y_line = y + size * (0.72 - i * 0.2)
            ax.plot(
                [x + size * 0.22, x + size * 0.78],
                [y_line, y_line],
                color=secondary,
                linewidth=lw,
                transform=ax.transAxes,
            )
        return

    if kind == "flow":
        ax.add_patch(Rectangle((x + size * 0.05, y + size * 0.52), size * 0.26, size * 0.18, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        ax.add_patch(Rectangle((x + size * 0.37, y + size * 0.52), size * 0.26, size * 0.18, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        ax.add_patch(Rectangle((x + size * 0.69, y + size * 0.22), size * 0.22, size * 0.18, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        for start, end in [((0.31, 0.61), (0.37, 0.61)), ((0.63, 0.61), (0.69, 0.31))]:
            ax.add_patch(
                FancyArrowPatch(
                    (x + size * start[0], y + size * start[1]),
                    (x + size * end[0], y + size * end[1]),
                    arrowstyle="-|>",
                    mutation_scale=8,
                    linewidth=lw,
                    color=secondary,
                    transform=ax.transAxes,
                )
            )
        return

    if kind == "rule":
        ax.add_patch(Rectangle((x + size * 0.12, y + size * 0.12), size * 0.72, size * 0.76, fill=False, edgecolor=color, linewidth=lw, transform=ax.transAxes))
        ax.add_patch(Rectangle((x + size * 0.2, y + size * 0.62), size * 0.44, size * 0.12, fill=False, edgecolor=secondary, linewidth=lw, transform=ax.transAxes))
        for i in range(2):
            y_line = y + size * (0.46 - i * 0.18)
            ax.plot(
                [x + size * 0.22, x + size * 0.76],
                [y_line, y_line],
                color=secondary,
                linewidth=lw,
                transform=ax.transAxes,
            )
        return


def draw_bilingual_input_panel(ax: plt.Axes, chinese_input: str, english_input: str) -> None:
    ax.set_axis_off()
    panel = FancyBboxPatch(
        (0.01, 0.01),
        0.98,
        0.98,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.0,
        edgecolor="#cbd5e1",
        facecolor="#f8fafc",
        transform=ax.transAxes,
    )
    ax.add_patch(panel)
    draw_icon(ax, "house", 0.04, 0.89, size=0.065)
    draw_icon(ax, "sensor", 0.11, 0.89, size=0.065)
    draw_icon(ax, "light", 0.18, 0.89, size=0.065)
    ax.text(0.28, 0.94, "Bilingual User Inputs", fontsize=12.5, fontweight="bold", color="#1f2937", va="top", transform=ax.transAxes)

    cn_box = FancyBboxPatch(
        (0.05, 0.54),
        0.9,
        0.26,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=0.8,
        edgecolor="#d8dee9",
        facecolor="#ffffff",
        transform=ax.transAxes,
    )
    en_box = FancyBboxPatch(
        (0.05, 0.18),
        0.9,
        0.26,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=0.8,
        edgecolor="#d8dee9",
        facecolor="#ffffff",
        transform=ax.transAxes,
    )
    ax.add_patch(cn_box)
    ax.add_patch(en_box)
    ax.text(0.08, 0.76, "Chinese input", fontsize=10.5, fontweight="bold", color="#355070", va="top", transform=ax.transAxes)
    ax.text(0.08, 0.65, format_text_block(chinese_input, width=18, max_lines=7), fontsize=10.5, color="#111827", va="top", transform=ax.transAxes)
    ax.text(0.08, 0.40, "English input", fontsize=10.5, fontweight="bold", color="#355070", va="top", transform=ax.transAxes)
    ax.text(0.08, 0.29, format_text_block(english_input, width=24, max_lines=7), fontsize=10.2, color="#111827", va="top", transform=ax.transAxes)


def parse_mermaid_flowchart(mermaid_diagram: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    node_pattern = re.compile(r'^\s*([A-Za-z0-9_]+)\["(.*)"\]\s*$')
    edge_pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)\s*$")
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str]] = []
    for raw_line in mermaid_diagram.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("flowchart "):
            continue
        node_match = node_pattern.match(line)
        if node_match:
            nodes[node_match.group(1)] = node_match.group(2)
            continue
        edge_match = edge_pattern.match(line)
        if edge_match:
            edges.append((edge_match.group(1), edge_match.group(2)))
    return nodes, edges


def split_mermaid_levels(nodes: dict[str, str]) -> dict[str, int]:
    levels: dict[str, int] = {}
    for node_id in nodes:
        if node_id == "RULE":
            levels[node_id] = 0
        elif node_id == "TRIGGER":
            levels[node_id] = 1
        elif node_id == "MODE":
            levels[node_id] = 1
        elif node_id == "CONDITIONS":
            levels[node_id] = 2
        elif node_id == "ACTIONS":
            levels[node_id] = 3
        elif node_id.startswith("C"):
            levels[node_id] = 4
        elif node_id.startswith("A"):
            levels[node_id] = 4
        else:
            levels[node_id] = 4
    return levels


def render_mermaid_diagram(ax: plt.Axes, mermaid_diagram: str, *, title: str = "Mermaid Diagram") -> None:
    ax.set_axis_off()
    panel = FancyBboxPatch(
        (0.01, 0.01),
        0.98,
        0.98,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=0.9,
        edgecolor="#cbd5e1",
        facecolor="#f8fafc",
        transform=ax.transAxes,
    )
    ax.add_patch(panel)
    draw_icon(ax, "flow", 0.04, 0.89, size=0.07)
    ax.text(0.15, 0.94, title, fontsize=12, fontweight="bold", color="#1f2937", va="top", transform=ax.transAxes)

    nodes, edges = parse_mermaid_flowchart(mermaid_diagram)
    levels = split_mermaid_levels(nodes)
    level_groups: dict[int, list[str]] = {}
    for node_id, level in levels.items():
        level_groups.setdefault(level, []).append(node_id)

    positions: dict[str, tuple[float, float]] = {}
    if "RULE" in nodes:
        positions["RULE"] = (0.50, 0.82)
    if "TRIGGER" in nodes:
        positions["TRIGGER"] = (0.25, 0.62)
    if "MODE" in nodes:
        positions["MODE"] = (0.75, 0.62)
    if "CONDITIONS" in nodes:
        positions["CONDITIONS"] = (0.34, 0.34)
    if "ACTIONS" in nodes:
        positions["ACTIONS"] = (0.66, 0.34)

    condition_nodes = sorted([node_id for node_id in nodes if node_id.startswith("C")])
    action_nodes = sorted([node_id for node_id in nodes if node_id.startswith("A")])

    if condition_nodes:
        x_positions = _spread_positions(len(condition_nodes), center=0.08, span=0.08)
        for x, node_id in zip(x_positions, condition_nodes):
            positions[node_id] = (x, 0.15)
    if action_nodes:
        x_positions = _spread_positions(len(action_nodes), center=0.92, span=0.08)
        for x, node_id in zip(x_positions, action_nodes):
            positions[node_id] = (x, 0.15)

    for node_id in nodes:
        positions.setdefault(node_id, (0.50, 0.50))

    for source, target in edges:
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        ax.add_patch(
            FancyArrowPatch(
                (sx, sy - 0.035),
                (tx, ty + 0.035),
                arrowstyle="-|>",
                mutation_scale=9,
                linewidth=1.0,
                color="#64748b",
                connectionstyle="arc3,rad=0.0",
                transform=ax.transAxes,
            )
        )

    for node_id, label in nodes.items():
        x, y = positions[node_id]
        if node_id == "RULE":
            width = 0.24
            height = 0.08
        elif node_id in {"TRIGGER", "MODE"}:
            width = 0.22
            height = 0.085
        elif node_id in {"CONDITIONS", "ACTIONS"}:
            width = 0.13
            height = 0.075
        else:
            width = 0.18
            height = 0.085
        facecolor = "#ffffff"
        if node_id in {"RULE", "TRIGGER", "MODE"}:
            facecolor = "#edf2f7"
        elif node_id in {"CONDITIONS", "ACTIONS"}:
            facecolor = "#f8fafc"
        node_patch = FancyBboxPatch(
            (x - width / 2, y - height / 2),
            width,
            height,
            boxstyle="round,pad=0.015,rounding_size=0.02",
            linewidth=0.85,
            edgecolor="#94a3b8",
            facecolor=facecolor,
            transform=ax.transAxes,
        )
        ax.add_patch(node_patch)
        if node_id == "RULE":
            text_width = 18
            font_size = 8.3
        elif node_id in {"TRIGGER", "MODE"}:
            text_width = 16
            font_size = 8.2
        elif node_id in {"CONDITIONS", "ACTIONS"}:
            text_width = 10
            font_size = 7.8
        else:
            text_width = 11
            font_size = 7.6
        ax.text(
            x,
            y,
            format_text_block(label, width=text_width, max_lines=2),
            fontsize=font_size,
            color="#1f2937",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )


def _spread_positions(count: int, center: float, span: float) -> list[float]:
    if count <= 1:
        return [center]
    half = span / 2
    return list(np.linspace(center - half, center + half, count))


def draw_explanation_panel(ax: plt.Axes, explanation: str) -> None:
    ax.set_axis_off()
    panel = FancyBboxPatch(
        (0.01, 0.01),
        0.98,
        0.98,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=0.9,
        edgecolor="#cbd5e1",
        facecolor="#f8fafc",
        transform=ax.transAxes,
    )
    ax.add_patch(panel)
    draw_icon(ax, "rule", 0.04, 0.89, size=0.07)
    ax.text(0.15, 0.94, "Natural Language Explanation", fontsize=12, fontweight="bold", color="#1f2937", va="top", transform=ax.transAxes)
    ax.text(
        0.05,
        0.84,
        format_text_block(explanation, width=34, max_lines=15),
        fontsize=9.6,
        color="#111827",
        va="top",
        ha="left",
        transform=ax.transAxes,
    )


def build_structured_output_text(
    repaired_dsl: dict[str, Any],
    yaml_text: str,
    explanation: str,
) -> str:
    parts = [
        "Repaired DSL",
        json.dumps(repaired_dsl, ensure_ascii=False, indent=2),
        "",
        "YAML",
        yaml_text.strip(),
        "",
        "Explanation",
        explanation.strip(),
    ]
    return "\n".join(parts).strip() + "\n"


def write_case_bundle(
    case_dir: Path,
    chinese_input: str,
    english_input: str,
    repaired_dsl: dict[str, Any],
    yaml_text: str,
    explanation: str,
    mermaid_diagram: str,
) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    inputs_text = (
        "Chinese Input\n"
        f"{chinese_input.strip()}\n\n"
        "English Input\n"
        f"{english_input.strip()}\n"
    )
    (case_dir / "Bilingual User Inputs.txt").write_text(inputs_text, encoding="utf-8-sig")
    structured_text = build_structured_output_text(repaired_dsl, yaml_text, explanation)
    (case_dir / "Structured Output.txt").write_text(structured_text, encoding="utf-8-sig")

    fig = plt.figure(figsize=(7.0, 5.6))
    ax = fig.add_subplot(111)
    render_mermaid_diagram(ax, mermaid_diagram, title="Mermaid Diagram")
    save_figure(fig, case_dir / "Mermaid Diagram.png")


def get_case_client() -> Any:
    return MockLLMClient()


def build_case_bundle(
    case_dir: Path,
    title: str,
    chinese_input: str,
    english_input: str,
    client: Any,
) -> None:
    zh_result = process_rule(chinese_input, client)
    en_result = process_rule(english_input, client)

    canonical_result = zh_result if zh_result.get("repaired_dsl") else en_result
    repaired_dsl = canonical_result.get("repaired_dsl", {})
    yaml_text = canonical_result.get("yaml", "")
    explanation = canonical_result.get("explanation", "")
    mermaid_diagram = canonical_result.get("mermaid_diagram", "")

    write_case_bundle(
        case_dir,
        chinese_input,
        english_input,
        repaired_dsl,
        yaml_text,
        explanation,
        mermaid_diagram,
    )


def generate_all_visualizations() -> list[Path]:
    configure_style()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    comparison_metrics = parse_comparison_metrics()
    repair_summary = parse_repair_summary()
    repair_error_rows = parse_repair_error_table()
    structured_metrics = parse_structured_metrics()
    batch_payload = load_batch_results()
    category_rows = compute_category_metrics(batch_payload)

    outputs: list[Path] = []

    figure_specs = [
        (
            FIGURE_DIR / "dsl_vs_direct_yaml.png",
            lambda path: plot_dsl_vs_direct_yaml(comparison_metrics, path),
        ),
        (
            FIGURE_DIR / "repair_before_after.png",
            lambda path: plot_repair_before_after(repair_summary, path),
        ),
        (
            FIGURE_DIR / "repair_error_types.png",
            lambda path: plot_repair_error_types(repair_error_rows, path),
        ),
        (
            FIGURE_DIR / "category_robustness.png",
            lambda path: plot_category_robustness(category_rows, path),
        ),
        (
            FIGURE_DIR / "structured_ml_metrics.png",
            lambda path: plot_structured_ml_metrics(structured_metrics, path),
        ),
    ]

    for output_path, generator in figure_specs:
        generator(output_path)
        outputs.append(output_path)

    client = get_case_client()
    cleanup_case_figure_images()
    for case_name, title, chinese_input, english_input in CASE_SPECS:
        build_case_bundle(FIGURE_DIR / case_name, title, chinese_input, english_input, client)

    return outputs


def cleanup_case_figure_images() -> None:
    for path in FIGURE_DIR.glob("case_*.png"):
        path.unlink(missing_ok=True)


def main() -> None:
    outputs = generate_all_visualizations()
    print(f"Generated {len(outputs)} PNG figures in {FIGURE_DIR}")


if __name__ == "__main__":
    main()
