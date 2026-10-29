from scripts.verify_real_rag import check_chat, check_health, check_no_answer


def _source(page=2):
    return {
        "id": "a@1.0#p2c1",
        "document_id": "a",
        "organization_id": "demo-org",
        "version": "1.0",
        "title": "空压机维修规范",
        "page": page,
        "chunk_index": 1,
        "snippet": "排气温度过高排查",
        "score": 6.4,
    }


def _chat(**overrides):
    payload = {
        "status": "ok",
        "is_mock": False,
        "is_demo": False,
        "sources": [_source()],
        "statements": [
            {
                "type": "fact",
                "text": "排气温度过高排查",
                "source_ids": ["a@1.0#p2c1"],
            }
        ],
    }
    payload.update(overrides)
    return payload


def _health(**overrides):
    payload = {
        "status": "ok",
        "llm_provider": "openai",
        "device_provider": "http",
    }
    payload.update(overrides)
    return payload


def test_ready_health_and_chat_pass():
    assert check_health(_health()) == []
    assert check_chat(_chat()) == []


def test_mock_and_static_are_rejected():
    health_errors = check_health(
        _health(llm_provider="mock", device_provider="static")
    )
    chat_errors = check_chat(_chat(is_mock=True, is_demo=True))

    assert any("llm_provider" in error for error in health_errors)
    assert any("device_provider" in error for error in health_errors)
    assert any("is_mock" in error for error in chat_errors)
    assert any("is_demo" in error for error in chat_errors)


def test_missing_source_fields_are_rejected():
    source = _source()
    del source["version"]

    errors = check_chat(_chat(sources=[source]))

    assert any("version" in error for error in errors)


def test_fact_must_reference_known_sources():
    errors = check_chat(
        _chat(
            statements=[
                {
                    "type": "fact",
                    "text": "无依据",
                    "source_ids": ["missing"],
                }
            ]
        )
    )

    assert any("未知证据" in error for error in errors)


def test_unknown_page_is_allowed():
    assert check_chat(_chat(sources=[_source(page=None)])) == []


def test_missing_page_field_is_rejected():
    source = _source()
    del source["page"]

    errors = check_chat(_chat(sources=[source]))

    assert any("page 缺失" in error for error in errors)


def test_no_answer_rejects_evidence():
    assert check_no_answer({"status": "no_answer", "sources": []}) == []
    errors = check_no_answer(
        {"status": "no_answer", "sources": [_source()]}
    )

    assert any("不应返回证据" in error for error in errors)
