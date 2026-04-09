from __future__ import annotations

import json
from collections import Counter
from typing import Any

import yaml


DSL_REQUIRED_TOP_LEVEL = ("rule_name", "trigger", "conditions", "actions", "mode")
YAML_REQUIRED_TOP_LEVEL = ("alias", "trigger", "action", "mode")
VALID_WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def rate(count: int, total: int) -> str:
    return f"{safe_div(count, total) * 100:.2f}%"


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def parse_yaml_text(yaml_text: str) -> tuple[bool, Any]:
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        return False, None
    try:
        return True, yaml.safe_load(yaml_text)
    except Exception:
        return False, None


def is_complete_dsl(payload: dict[str, Any]) -> bool:
    return dsl_field_stats(payload)["complete"]


def dsl_field_fill_rate(payload: dict[str, Any]) -> float:
    return dsl_field_stats(payload)["fill_rate"]


def dsl_field_stats(payload: dict[str, Any]) -> dict[str, Any]:
    total = 0
    filled = 0

    def count(value: Any) -> None:
        nonlocal total, filled
        total += 1
        if value not in (None, "", [], {}):
            filled += 1

    if not isinstance(payload, dict):
        return {"complete": False, "filled": 0, "total": 0, "fill_rate": 0.0}

    for key in DSL_REQUIRED_TOP_LEVEL:
        count(payload.get(key))

    trigger = payload.get("trigger")
    if isinstance(trigger, dict):
        count(trigger.get("type"))
        trigger_type = trigger.get("type")
        if trigger_type == "time":
            count(trigger.get("at"))
        elif trigger_type == "state_change":
            count(trigger.get("entity"))
        elif trigger_type == "event":
            count(trigger.get("event_type"))

    for condition in payload.get("conditions", []) if isinstance(payload.get("conditions"), list) else []:
        if not isinstance(condition, dict):
            total += 1
            continue
        count(condition.get("type"))
        condition_type = condition.get("type")
        if condition_type == "state":
            count(condition.get("entity"))
            count(condition.get("expected_state"))
        elif condition_type == "time_range":
            count(condition.get("start"))
            count(condition.get("end"))
        elif condition_type == "weekday":
            count(condition.get("days"))

    for action in payload.get("actions", []) if isinstance(payload.get("actions"), list) else []:
        if not isinstance(action, dict):
            total += 2
            continue
        count(action.get("service"))
        count(action.get("entity"))

    complete = (
        isinstance(payload.get("trigger"), dict)
        and isinstance(payload.get("conditions"), list)
        and isinstance(payload.get("actions"), list)
        and bool(payload.get("actions"))
        and all(key in payload for key in DSL_REQUIRED_TOP_LEVEL)
    )
    return {
        "complete": complete,
        "filled": filled,
        "total": total,
        "fill_rate": safe_div(filled, total),
    }


def is_complete_yaml(payload: dict[str, Any]) -> bool:
    return yaml_field_stats(payload)["complete"]


def yaml_field_fill_rate(payload: dict[str, Any]) -> float:
    return yaml_field_stats(payload)["fill_rate"]


def yaml_field_stats(payload: dict[str, Any]) -> dict[str, Any]:
    total = 0
    filled = 0

    def count(value: Any) -> None:
        nonlocal total, filled
        total += 1
        if value not in (None, "", [], {}):
            filled += 1

    if not isinstance(payload, dict):
        return {"complete": False, "filled": 0, "total": 0, "fill_rate": 0.0}

    for key in YAML_REQUIRED_TOP_LEVEL:
        count(payload.get(key))

    trigger_list = payload.get("trigger")
    if isinstance(trigger_list, list) and trigger_list:
        trigger = trigger_list[0]
        if isinstance(trigger, dict):
            count(trigger.get("platform"))
            if trigger.get("platform") == "time":
                count(trigger.get("at"))
            elif trigger.get("platform") == "state":
                count(trigger.get("entity_id"))
            elif trigger.get("platform") == "event":
                count(trigger.get("event_type"))

    for action in payload.get("action", []) if isinstance(payload.get("action"), list) else []:
        if not isinstance(action, dict):
            total += 2
            continue
        count(action.get("service"))
        target = action.get("target")
        count(target.get("entity_id") if isinstance(target, dict) else None)

    complete = (
        all(key in payload for key in YAML_REQUIRED_TOP_LEVEL)
        and isinstance(payload.get("trigger"), list)
        and bool(payload.get("trigger"))
        and isinstance(payload.get("action"), list)
        and bool(payload.get("action"))
    )
    return {
        "complete": complete,
        "filled": filled,
        "total": total,
        "fill_rate": safe_div(filled, total),
    }


def validation_error_types(validation: dict[str, Any]) -> list[str]:
    if not isinstance(validation, dict):
        return []
    return [issue.get("type", "unknown") for issue in validation.get("errors", []) if isinstance(issue, dict)]


def has_any_error_type(validation: dict[str, Any], error_types: set[str]) -> bool:
    return any(error_type in error_types for error_type in validation_error_types(validation))


def error_combo(validation: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(set(validation_error_types(validation))))


def canonicalize_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonicalize_obj(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        canonical_items = [canonicalize_obj(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def exact_match(predicted: dict[str, Any], gold: dict[str, Any]) -> bool:
    return canonicalize_obj(predicted) == canonicalize_obj(gold)


def flatten_structure(value: Any, prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            flattened.update(flatten_structure(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            flattened.update(flatten_structure(item, next_prefix))
    else:
        flattened[prefix] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return flattened


def field_accuracy(predicted: dict[str, Any], gold: dict[str, Any]) -> float:
    pred_fields = flatten_structure(canonicalize_obj(predicted))
    gold_fields = flatten_structure(canonicalize_obj(gold))
    field_keys = set(pred_fields) | set(gold_fields)
    if not field_keys:
        return 1.0
    correct = sum(1 for key in field_keys if pred_fields.get(key) == gold_fields.get(key))
    return safe_div(correct, len(field_keys))


def extract_trigger_type(rule: dict[str, Any]) -> str | None:
    trigger = rule.get("trigger")
    return trigger.get("type") if isinstance(trigger, dict) else None


def extract_mode(rule: dict[str, Any]) -> str | None:
    mode = rule.get("mode")
    return mode if isinstance(mode, str) else None


def extract_entities(rule: dict[str, Any]) -> set[str]:
    entities: set[str] = set()
    trigger = rule.get("trigger")
    if isinstance(trigger, dict):
        entity = trigger.get("entity")
        if isinstance(entity, str):
            entities.add(entity)
        event_data = trigger.get("event_data")
        if isinstance(event_data, dict):
            event_entity = event_data.get("entity_id")
            if isinstance(event_entity, str):
                entities.add(event_entity)
    for condition in rule.get("conditions", []) if isinstance(rule.get("conditions"), list) else []:
        if isinstance(condition, dict):
            entity = condition.get("entity")
            if isinstance(entity, str):
                entities.add(entity)
    for action in rule.get("actions", []) if isinstance(rule.get("actions"), list) else []:
        if isinstance(action, dict):
            entity = action.get("entity")
            if isinstance(entity, str):
                entities.add(entity)
    return entities


def extract_services(rule: dict[str, Any]) -> set[str]:
    services: set[str] = set()
    for action in rule.get("actions", []) if isinstance(rule.get("actions"), list) else []:
        if isinstance(action, dict):
            service = action.get("service")
            if isinstance(service, str):
                services.add(service)
    return services


def extract_action_domains(rule: dict[str, Any]) -> set[str]:
    return {service.split(".", 1)[0] for service in extract_services(rule)}


def extract_condition_types(rule: dict[str, Any]) -> list[str]:
    types: list[str] = []
    for condition in rule.get("conditions", []) if isinstance(rule.get("conditions"), list) else []:
        if isinstance(condition, dict) and isinstance(condition.get("type"), str):
            types.append(condition["type"])
    return types


def extract_weekdays(rule: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for condition in rule.get("conditions", []) if isinstance(rule.get("conditions"), list) else []:
        if isinstance(condition, dict) and condition.get("type") == "weekday":
            for day in condition.get("days", []):
                if isinstance(day, str):
                    labels.append(day)
    return labels


def action_signature_set(rule: dict[str, Any]) -> set[str]:
    signatures: set[str] = set()
    for action in rule.get("actions", []) if isinstance(rule.get("actions"), list) else []:
        if not isinstance(action, dict):
            continue
        signature = {
            "service": action.get("service"),
            "entity": action.get("entity"),
            "data": canonicalize_obj(action.get("data", {})),
        }
        signatures.add(json.dumps(signature, ensure_ascii=False, sort_keys=True))
    return signatures


def condition_signature_set(rule: dict[str, Any]) -> set[str]:
    signatures: set[str] = set()
    for condition in rule.get("conditions", []) if isinstance(rule.get("conditions"), list) else []:
        if not isinstance(condition, dict):
            continue
        signatures.add(json.dumps(canonicalize_obj(condition), ensure_ascii=False, sort_keys=True))
    return signatures


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 1.0
    return safe_div(len(left & right), len(union))


def set_precision_recall_f1(predicted: set[str], gold: set[str]) -> dict[str, float]:
    true_positive = len(predicted & gold)
    precision = safe_div(true_positive, len(predicted))
    recall = safe_div(true_positive, len(gold))
    f1 = safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def classification_metrics(
    predicted_labels: list[str | None],
    gold_labels: list[str | None],
    labels: set[str],
) -> dict[str, float]:
    label_scores: list[dict[str, float]] = []
    correct = 0
    total = min(len(predicted_labels), len(gold_labels))

    for predicted, gold in zip(predicted_labels, gold_labels):
        if predicted == gold:
            correct += 1

    for label in labels:
        tp = fp = fn = 0
        for predicted, gold in zip(predicted_labels, gold_labels):
            if predicted == label and gold == label:
                tp += 1
            elif predicted == label and gold != label:
                fp += 1
            elif predicted != label and gold == label:
                fn += 1
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
        label_scores.append({"precision": precision, "recall": recall, "f1": f1})

    return {
        "accuracy": safe_div(correct, total),
        "precision": average([score["precision"] for score in label_scores]),
        "recall": average([score["recall"] for score in label_scores]),
        "f1": average([score["f1"] for score in label_scores]),
    }


def multilabel_macro_f1(predicted_sets: list[set[str]], gold_sets: list[set[str]]) -> float:
    label_space = set().union(*predicted_sets, *gold_sets) if predicted_sets or gold_sets else set()
    if not label_space:
        return 1.0
    f1_scores: list[float] = []
    for label in label_space:
        tp = fp = fn = 0
        for predicted, gold in zip(predicted_sets, gold_sets):
            if label in predicted and label in gold:
                tp += 1
            elif label in predicted and label not in gold:
                fp += 1
            elif label not in predicted and label in gold:
                fn += 1
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1_scores.append(safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0)
    return average(f1_scores)


def multilabel_micro_prf(predicted_sets: list[set[str]], gold_sets: list[set[str]]) -> dict[str, float]:
    tp = fp = fn = 0
    for predicted, gold in zip(predicted_sets, gold_sets):
        tp += len(predicted & gold)
        fp += len(predicted - gold)
        fn += len(gold - predicted)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def top_error_combos(combos: list[tuple[str, ...]], top_n: int = 10) -> list[tuple[tuple[str, ...], int]]:
    filtered = [combo for combo in combos if combo]
    counter = Counter(filtered)
    return counter.most_common(top_n)
