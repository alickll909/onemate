from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DISCLAIMER
from backend.deepseek import (
    DeepSeekEmptyResponseError,
    DeepSeekHTTPStatusError,
    DeepSeekNetworkError,
    DeepSeekTimeoutError,
    call_deepseek,
)
from backend.report_validation import detect_abnormal_items, validate_report
from backend.schemas import KeyPayload, PromptPayload
from backend.store import db

MAX_REPORTS = 20

app = FastAPI(title="OneMate Blood Report Interpreter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/prompt")
def get_prompt() -> dict[str, str]:
    return {"prompt": db["system_prompt"]}


@app.post("/api/prompt")
def save_prompt(payload: PromptPayload) -> dict[str, str]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt 不能为空")
    db["system_prompt"] = prompt
    return {"prompt": db["system_prompt"]}


@app.get("/api/key")
def get_key_status() -> dict[str, bool]:
    return {"configured": bool(db["api_key"])}


@app.post("/api/key")
def save_key(payload: KeyPayload) -> dict[str, bool]:
    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="api_key 不能为空")
    db["api_key"] = api_key
    return {"configured": bool(db["api_key"])}


def save_report_history(
    report: dict[str, Any],
    interpretation: str,
    abnormal_items: list[dict[str, Any]],
) -> dict[str, Any]:
    record = {
        "id": str(db["next_report_id"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "test_name": report["test_name"],
        "patient_id": report["patient_id"],
        "sample_time": report["sample_time"],
        "interpretation": interpretation,
        "abnormal_items": abnormal_items,
        "disclaimer": DISCLAIMER,
    }
    db["next_report_id"] += 1
    db["reports"].insert(0, record)
    del db["reports"][MAX_REPORTS:]
    return record


@app.get("/api/reports")
def list_reports() -> dict[str, list[dict[str, Any]]]:
    return {"reports": db["reports"]}


@app.post("/api/interpret")
async def interpret(report_payload: dict[str, Any]) -> dict[str, Any]:
    report = validate_report(report_payload)
    abnormal_items = detect_abnormal_items(report)

    if not db["api_key"]:
        raise HTTPException(status_code=400, detail="未配置 DeepSeek API Key")

    try:
        interpretation = await call_deepseek(
            report=report,
            abnormal_items=abnormal_items,
            system_prompt=db["system_prompt"],
            api_key=db["api_key"],
        )
    except DeepSeekTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (DeepSeekHTTPStatusError, DeepSeekNetworkError, DeepSeekEmptyResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return save_report_history(report, interpretation, abnormal_items)
