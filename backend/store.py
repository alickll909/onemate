from __future__ import annotations

from typing import Any

from backend.config import DEFAULT_SYSTEM_PROMPT

db: dict[str, Any] = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "api_key": "",
    "reports": [],
    "next_report_id": 1,
}


def reset_db() -> None:
    db["system_prompt"] = DEFAULT_SYSTEM_PROMPT
    db["api_key"] = ""
    db["reports"] = []
    db["next_report_id"] = 1
