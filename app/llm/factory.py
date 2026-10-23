from __future__ import annotations

import os

from app.config import is_production
from app.llm.base import BaseLLM
from app.llm.mock import MockLLM
from app.llm.openai import OpenAILLM


def build_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "openai":
        return OpenAILLM()
    if is_production():
        raise ValueError("生产环境不允许使用 LLM_PROVIDER=mock")
    return MockLLM()
