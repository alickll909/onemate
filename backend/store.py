from __future__ import annotations

from backend.config import DEFAULT_SYSTEM_PROMPT

db: dict[str, str] = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "api_key": "",
}


def reset_db() -> None:
    db["system_prompt"] = DEFAULT_SYSTEM_PROMPT
    db["api_key"] = ""
