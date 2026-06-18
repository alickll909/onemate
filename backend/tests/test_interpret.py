from __future__ import annotations

import copy
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from backend.config import DISCLAIMER, DEFAULT_SYSTEM_PROMPT
from backend.deepseek import (
    DeepSeekEmptyResponseError,
    DeepSeekHTTPStatusError,
    DeepSeekNetworkError,
    DeepSeekTimeoutError,
    call_deepseek,
)
from backend.report_validation import detect_abnormal_items, validate_report
from backend.store import reset_db

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_db() -> None:
    reset_db()


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


@pytest.fixture
def sample_report() -> dict[str, Any]:
    with (ROOT / "blood_testcase.json").open(encoding="utf-8") as file:
        return json.load(file)


def test_validate_report_accepts_sample_json(sample_report: dict[str, Any]) -> None:
    assert validate_report(sample_report) == sample_report


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        ({"patient_id": "P0001", "sample_time": "2026-06-18", "results": {}}, "缺少顶层字段: test_name"),
        (
            {"test_name": "CBC", "patient_id": "P0001", "sample_time": "2026-06-18", "results": []},
            "results 必须是非空对象",
        ),
        (
            {
                "test_name": "CBC",
                "patient_id": "P0001",
                "sample_time": "2026-06-18",
                "results": {"wbc": {"name": "白细胞计数", "value": "abc", "unit": "10^9/L", "reference_range": "4-10"}},
            },
            "指标 wbc 的 value 必须是数值",
        ),
    ],
)
def test_interpret_rejects_invalid_report_payloads(
    client: TestClient,
    payload: dict[str, Any],
    expected_detail: str,
) -> None:
    response = client.post("/api/interpret", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail


def test_detect_abnormal_items_flags_wbc_hgb_plt(sample_report: dict[str, Any]) -> None:
    report = copy.deepcopy(sample_report)
    report["results"]["wbc"]["value"] = 12.5
    report["results"]["hgb"]["value"] = 108
    report["results"]["plt"]["value"] = 398

    abnormal_items = detect_abnormal_items(validate_report(report))

    assert [(item["key"], item["direction"]) for item in abnormal_items] == [
        ("wbc", "high"),
        ("hgb", "low"),
        ("plt", "high"),
    ]


def test_prompt_can_be_saved_and_read(client: TestClient) -> None:
    response = client.post("/api/prompt", json={"prompt": "  新 Prompt：保持审慎表达  "})

    assert response.status_code == 200
    assert response.json() == {"prompt": "新 Prompt：保持审慎表达"}
    assert client.get("/api/prompt").json() == {"prompt": "新 Prompt：保持审慎表达"}


def test_prompt_defaults_to_medical_safety_requirements(client: TestClient) -> None:
    prompt = client.get("/api/prompt").json()["prompt"]

    assert prompt == DEFAULT_SYSTEM_PROMPT
    assert "严禁编造诊断" in prompt
    assert "reference_range" in prompt
    assert "异常检测列表" in prompt
    assert "白细胞升高可能提示存在感染" in prompt
    assert "[[ABNORMAL:指标名称|数值 单位]]" in prompt


def test_interpret_returns_clear_error_when_api_key_is_missing(
    client: TestClient,
    sample_report: dict[str, Any],
) -> None:
    response = client.post("/api/interpret", json=sample_report)

    assert response.status_code == 400
    assert response.json()["detail"] == "未配置 DeepSeek API Key"


def test_interpret_returns_ai_result_abnormal_items_and_disclaimer(
    client: TestClient,
    sample_report: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = copy.deepcopy(sample_report)
    report["results"]["wbc"]["value"] = 12.5
    report["results"]["hgb"]["value"] = 108
    report["results"]["plt"]["value"] = 398

    async def fake_call_deepseek(**kwargs: Any) -> str:
        assert kwargs["api_key"] == "sk-test"
        assert kwargs["system_prompt"] == DEFAULT_SYSTEM_PROMPT
        assert [item["key"] for item in kwargs["abnormal_items"]] == ["wbc", "hgb", "plt"]
        return "总体印象：[[ABNORMAL:白细胞计数|12.5 10^9/L]] 升高。"

    monkeypatch.setattr(main, "call_deepseek", fake_call_deepseek)
    client.post("/api/key", json={"api_key": "sk-test"})

    response = client.post("/api/interpret", json=report)

    assert response.status_code == 200
    data = response.json()
    assert data["interpretation"].startswith("总体印象")
    assert [item["key"] for item in data["abnormal_items"]] == ["wbc", "hgb", "plt"]
    assert data["disclaimer"] == DISCLAIMER


def test_call_deepseek_returns_content(sample_report: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert request.headers["Authorization"] == "Bearer sk-test"
        assert body["model"] == "deepseek-chat"
        assert body["messages"][0]["content"] == DEFAULT_SYSTEM_PROMPT
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "解读结果"}}]},
            request=request,
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            return await call_deepseek(sample_report, [], DEFAULT_SYSTEM_PROMPT, "sk-test", client=http_client)

    assert asyncio.run(run()) == "解读结果"


def test_call_deepseek_maps_http_status_error(sample_report: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"}, request=request)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            await call_deepseek(sample_report, [], DEFAULT_SYSTEM_PROMPT, "sk-test", client=http_client)

    with pytest.raises(DeepSeekHTTPStatusError, match="HTTP 401"):
        asyncio.run(run())


def test_call_deepseek_maps_timeout(sample_report: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            await call_deepseek(sample_report, [], DEFAULT_SYSTEM_PROMPT, "sk-test", client=http_client)

    with pytest.raises(DeepSeekTimeoutError, match="调用超时"):
        asyncio.run(run())


def test_call_deepseek_maps_network_error(sample_report: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cannot connect", request=request)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            await call_deepseek(sample_report, [], DEFAULT_SYSTEM_PROMPT, "sk-test", client=http_client)

    with pytest.raises(DeepSeekNetworkError, match="ConnectError"):
        asyncio.run(run())


def test_call_deepseek_rejects_empty_content(sample_report: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  "}}]},
            request=request,
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            await call_deepseek(sample_report, [], DEFAULT_SYSTEM_PROMPT, "sk-test", client=http_client)

    with pytest.raises(DeepSeekEmptyResponseError, match="返回内容为空"):
        asyncio.run(run())
