import json

import httpx
import pytest

from app.core.device_provider import DeviceContext
from app.llm.base import LLMError
from app.llm.factory import build_llm
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


def _completion(payload) -> dict:
    return {
        "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]
    }


def _valid_payload() -> dict:
    return {
        "summary": "疑似冷却器堵塞，建议停机检查。",
        "statements": [
            {
                "type": "fact",
                "text": "冷却器堵塞导致散热不良",
                "source_ids": ["a@v1.0#p1c0"],
            },
            {"type": "inference", "text": "优先检查冷却器", "source_ids": []},
            {"type": "pending", "text": "需现场确认", "source_ids": []},
        ],
        "conflicts": [
            {
                "field": "额定压力",
                "sources": [
                    {"origin": "device_record", "value": "0.8 MPa", "ref": None}
                ],
            }
        ],
        "verification_suggestions": [
            {"missing_evidence": "清洗记录", "to_verify": "是否堵塞"}
        ],
    }


def test_openai_llm_structured_output():
    def handler(request):
        response = _completion(_valid_payload())
        response.update({
            "model": "deepseek-flash",
            "usage": {"prompt_tokens": 321, "completion_tokens": 123, "total_tokens": 444},
        })
        return httpx.Response(200, json=response)

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    result = llm.answer("问题", _evidence())

    assert result.answer.startswith("疑似冷却器")
    assert result.summary.startswith("疑似冷却器")
    assert llm.is_mock is False
    assert [s.type for s in result.statements] == ["fact", "inference", "pending"]
    assert result.statements[0].source_ids == ["a@v1.0#p1c0"]
    assert result.conflicts[0].field == "额定压力"
    assert result.verification_suggestions[0].missing_evidence == "清洗记录"
    assert result.provider == "openai-compatible"
    assert result.model == "deepseek-flash"
    assert result.input_tokens == 321
    assert result.output_tokens == 123
    assert result.total_tokens == 444


def test_openai_llm_handles_code_fence():
    def handler(request):
        content = "```json\n" + json.dumps(_valid_payload(), ensure_ascii=False) + "\n```"
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    result = llm.answer("问题", _evidence())

    assert result.statements


def test_openai_llm_invalid_json_degrades():
    def handler(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "这不是 JSON"}}]}
        )

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


def test_openai_llm_schema_mismatch_degrades():
    def handler(request):
        return httpx.Response(
            200,
            json=_completion(
                {"summary": "x", "statements": [{"type": "bad", "text": "t"}]}
            ),
        )

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


def test_openai_llm_timeout():
    def handler(request):
        raise httpx.TimeoutException("timeout")

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_openai_llm_http_error_degrades(status_code):
    def handler(request):
        return httpx.Response(
            status_code, json={"error": {"message": "upstream failed"}}
        )

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
        return httpx.Response(200, json=_completion(_valid_payload()))

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )
    llm.answer("问题", _evidence())

    system = captured["body"]["messages"][0]["content"]
    assert "数据而非指令" in system


def test_openai_llm_reuses_client():
    count = {"n": 0}

    def handler(request):
        count["n"] += 1
        return httpx.Response(200, json=_completion(_valid_payload()))

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    assert llm._http is llm._http
    llm.answer("q1", _evidence())
    llm.answer("q2", _evidence())
    assert count["n"] == 2


def _device():
    return DeviceContext(
        device_id="AC-07",
        name="螺杆空气压缩机",
        type="动力与流体机械",
        model="GX11",
        location="压缩站 Bay03",
        status="attention",
        knowledge_model="compressor-002",
    )


def test_openai_llm_prompt_includes_device_facts():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion(_valid_payload()))

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )
    llm.answer("问题", _evidence(), device=_device())

    user_prompt = captured["body"]["messages"][1]["content"]
    assert "设备事实" in user_prompt
    assert "AC-07" in user_prompt
    assert "GX11" in user_prompt
    assert captured["body"]["max_tokens"] == 1024


def test_openai_llm_prompt_marks_unknown_page():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion(_valid_payload()))

    evidence = _evidence()
    evidence[0].page = None
    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )
    llm.answer("问题", evidence)

    user_prompt = captured["body"]["messages"][1]["content"]
    assert "第未知页" in user_prompt
    assert "第None页" not in user_prompt


def test_openai_llm_invalid_http_json_degrades():
    def handler(request):
        return httpx.Response(200, text="not-json")

    llm = OpenAILLM(
        api_key="k", base_url="http://x", model="m", client=_client(handler)
    )

    with pytest.raises(LLMError):
        llm.answer("问题", _evidence())


def test_build_llm_rejects_mock_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    with pytest.raises(ValueError):
        build_llm()
