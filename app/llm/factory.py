from __future__ import annotations

import os

from app.llm.base import BaseLLM
from app.llm.mock import MockLLM
from app.llm.openai import OpenAILLM


def build_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "openai":
        return OpenAILLM()
    return MockLLM()
