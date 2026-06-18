from __future__ import annotations

from pydantic import BaseModel, Field


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
