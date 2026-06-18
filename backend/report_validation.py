from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

REQUIRED_TOP_FIELDS = ["test_name", "patient_id", "sample_time", "results"]
REQUIRED_ITEM_FIELDS = ["name", "value", "unit", "reference_range"]


def validate_report(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="请求体必须是 JSON 对象")

    missing = [field for field in REQUIRED_TOP_FIELDS if field not in data]
    if missing:
        raise HTTPException(status_code=422, detail=f"缺少顶层字段: {', '.join(missing)}")

    if not isinstance(data["results"], dict) or not data["results"]:
        raise HTTPException(status_code=422, detail="results 必须是非空对象")

    for key, item in data["results"].items():
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail=f"指标 {key} 必须是对象")
        missing_item = [field for field in REQUIRED_ITEM_FIELDS if field not in item]
        if missing_item:
            raise HTTPException(
                status_code=422,
                detail=f"指标 {key} 缺少字段: {', '.join(missing_item)}",
            )
        try:
            float(item["value"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"指标 {key} 的 value 必须是数值")

    return data


def parse_reference_range(raw_range: Any) -> tuple[float, float] | None:
    if not isinstance(raw_range, str):
        return None
    normalized = raw_range.replace("－", "-").replace("—", "-").replace("~", "-").replace("～", "-")
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", normalized)
    if not match:
        return None
    low, high = float(match.group(1)), float(match.group(2))
    if low > high:
        low, high = high, low
    return low, high


def detect_abnormal_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    abnormal_items: list[dict[str, Any]] = []
    for key, item in report["results"].items():
        parsed_range = parse_reference_range(item["reference_range"])
        if not parsed_range:
            continue
        low, high = parsed_range
        value = float(item["value"])
        if value < low or value > high:
            abnormal_items.append(
                {
                    "key": key,
                    "name": str(item["name"]),
                    "value": value,
                    "unit": str(item["unit"]),
                    "reference_range": str(item["reference_range"]),
                    "direction": "low" if value < low else "high",
                }
            )
    return abnormal_items
