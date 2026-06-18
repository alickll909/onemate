from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT_SECONDS, DEEPSEEK_URL


class DeepSeekError(Exception):
    pass


class DeepSeekHTTPStatusError(DeepSeekError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"DeepSeek 调用失败: HTTP {status_code}")
        self.status_code = status_code


class DeepSeekTimeoutError(DeepSeekError):
    def __init__(self) -> None:
        super().__init__("DeepSeek 调用超时，请稍后重试")


class DeepSeekNetworkError(DeepSeekError):
    def __init__(self, error_name: str) -> None:
        super().__init__(f"DeepSeek 网络错误: {error_name}")


class DeepSeekEmptyResponseError(DeepSeekError):
    def __init__(self) -> None:
        super().__init__("DeepSeek 返回内容为空")


def build_request_body(
    report: dict[str, Any],
    abnormal_items: list[dict[str, Any]],
    system_prompt: str,
) -> dict[str, Any]:
    user_content = {
        "blood_report": report,
        "pre_detected_abnormal_items": abnormal_items,
        "output_requirement": "请优先覆盖 pre_detected_abnormal_items 中的异常项，并使用 [[ABNORMAL:指标名称|数值 单位]] 标记。",
    }
    return {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_content, ensure_ascii=False, indent=2)},
        ],
        "temperature": 0.2,
    }


async def call_deepseek(
    report: dict[str, Any],
    abnormal_items: list[dict[str, Any]],
    system_prompt: str,
    api_key: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    request_body = build_request_body(report, abnormal_items, system_prompt)

    async def post(active_client: httpx.AsyncClient) -> httpx.Response:
        return await active_client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
        )

    try:
        if client is None:
            async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as active_client:
                response = await post(active_client)
        else:
            response = await post(client)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise DeepSeekHTTPStatusError(exc.response.status_code) from exc
    except httpx.TimeoutException as exc:
        raise DeepSeekTimeoutError() from exc
    except httpx.HTTPError as exc:
        raise DeepSeekNetworkError(exc.__class__.__name__) from exc

    data = response.json()
    interpretation = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not interpretation:
        raise DeepSeekEmptyResponseError()
    return interpretation
