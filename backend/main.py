from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


DISCLAIMER = "AI建议仅供参考，请以临床医生诊断为准。"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

DEFAULT_SYSTEM_PROMPT = """你是医智通 OneMate 的血常规报告解读智能体，面向临床医生提供辅助解读。

任务：
1. 根据用户提交的血常规 JSON 中每个指标的 reference_range 判断异常，数值低于下限或高于上限均为异常。
2. 对每个异常项用通俗、审慎的中文解释可能临床意义，例如白细胞升高可能提示感染、炎症或应激反应。
3. 异常项必须使用固定标记格式：[[ABNORMAL:指标名称|数值 单位]]，例如 [[ABNORMAL:白细胞计数|12.5 10^9/L]]。
4. 正常项可简要说明，无需逐项展开过多。
5. 严禁编造诊断、病因或治疗方案；无法确认时必须明确说明“仅凭血常规无法确认，需要结合病史、体征和其他检查”。
6. 输出结构建议包含：总体印象、异常指标解读、建议关注、局限性说明。
"""

db: dict[str, str] = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "api_key": "",
}

app = FastAPI(title="OneMate Blood Report Interpreter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptPayload(BaseModel):
    prompt: str = Field(min_length=1)


class KeyPayload(BaseModel):
    api_key: str = Field(min_length=1)


class AbnormalItem(BaseModel):
    key: str
    name: str
    value: float
    unit: str
    reference_range: str
    direction: str


def validate_report(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="请求体必须是 JSON 对象")

    required_top_fields = ["test_name", "patient_id", "sample_time", "results"]
    missing = [field for field in required_top_fields if field not in data]
    if missing:
        raise HTTPException(status_code=422, detail=f"缺少顶层字段: {', '.join(missing)}")

    if not isinstance(data["results"], dict) or not data["results"]:
        raise HTTPException(status_code=422, detail="results 必须是非空对象")

    required_item_fields = ["name", "value", "unit", "reference_range"]
    for key, item in data["results"].items():
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail=f"指标 {key} 必须是对象")
        missing_item = [field for field in required_item_fields if field not in item]
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


@app.get("/api/prompt")
def get_prompt() -> dict[str, str]:
    return {"prompt": db["system_prompt"]}


@app.post("/api/prompt")
def save_prompt(payload: PromptPayload) -> dict[str, str]:
    db["system_prompt"] = payload.prompt.strip()
    return {"prompt": db["system_prompt"]}


@app.get("/api/key")
def get_key_status() -> dict[str, bool]:
    return {"configured": bool(db["api_key"])}


@app.post("/api/key")
def save_key(payload: KeyPayload) -> dict[str, bool]:
    db["api_key"] = payload.api_key.strip()
    return {"configured": bool(db["api_key"])}


@app.post("/api/interpret")
async def interpret(report_payload: dict[str, Any]) -> dict[str, Any]:
    report = validate_report(report_payload)
    abnormal_items = detect_abnormal_items(report)

    if not db["api_key"]:
        raise HTTPException(status_code=400, detail="未配置 DeepSeek API Key")

    user_content = {
        "blood_report": report,
        "pre_detected_abnormal_items": abnormal_items,
        "output_requirement": "请优先覆盖 pre_detected_abnormal_items 中的异常项，并使用 [[ABNORMAL:指标名称|数值 单位]] 标记。",
    }
    request_body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": db["system_prompt"]},
            {"role": "user", "content": json.dumps(user_content, ensure_ascii=False, indent=2)},
        ],
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {db['api_key']}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败: HTTP {exc.response.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="DeepSeek 调用超时，请稍后重试")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 网络错误: {exc.__class__.__name__}")

    data = response.json()
    interpretation = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not interpretation:
        raise HTTPException(status_code=502, detail="DeepSeek 返回内容为空")

    return {
        "interpretation": interpretation,
        "abnormal_items": abnormal_items,
        "disclaimer": DISCLAIMER,
    }
