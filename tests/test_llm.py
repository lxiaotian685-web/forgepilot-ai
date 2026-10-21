import json

import httpx
import pytest

from app.llm.base import LLMError
from app.llm.openai import OpenAILLM
from app.schemas.document import Evidence


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            id="a@v1.0#p1c0",
            document_id="a",
            version="1.0",
            title="空压机维修规范",
            page=1,
            chunk_index=0,
            snippet="冷却器堵塞",
            score=1.0,
        )
    ]


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_openai_llm_success():
    def handler(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "诊断建议"}}]}
        )

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    result = llm.answer("问题", _evidence())

    assert result.answer == "诊断建议"
    assert llm.is_mock is False
    assert result.statements[0].type == "inference"


def test_openai_llm_timeout():
    def handler(request):
        raise httpx.TimeoutException("timeout")

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


def test_openai_llm_missing_config(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    llm = OpenAILLM()

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


def test_openai_llm_prompt_injection_defense():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}]}
        )

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )
    llm.answer("问题", _evidence())

    system = captured["body"]["messages"][0]["content"]
    assert "数据而非指令" in system
