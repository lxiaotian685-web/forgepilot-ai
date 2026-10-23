import httpx

from app.core.device_provider import HttpDeviceProvider, StaticDeviceProvider
from app.core.store import KnowledgeBase
from app.llm.base import LLMError
from app.llm.mock import MockLLM
from app.schemas.chat import Conflict, ConflictSource, Statement
from app.services.rag import RAGService


class _FailingLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        raise LLMError("boom")


class _BadCitationLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences)
        result.statements = [
            Statement(type="fact", text="x", source=None, source_ids=["not-in-evidence"])
        ]
        return result


class _MixedCitationLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences)
        result.answer = "有效事实；无依据事实"
        result.summary = "混合引用摘要"
        result.statements = [
            Statement(type="fact", text="有效事实", source_ids=[evidences[0].id]),
            Statement(
                type="fact", text="无依据事实", source_ids=["invalid-id"]
            ),
        ]
        return result


class _WrongDeviceProvider:
    def get_device(self, device_id, auth=None):
        return StaticDeviceProvider().get_device("P-102")

    def close(self):
        pass


class _ConflictingLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences)
        result.conflicts = [
            Conflict(
                field="额定排气压力",
                sources=[
                    ConflictSource(origin="device_record", value="0.8 MPa"),
                    ConflictSource(
                        origin="document", value="0.7 MPa", ref=evidences[0].id
                    ),
                ],
            )
        ]
        return result


def _make_service(llm) -> RAGService:
    kb = KnowledgeBase()
    kb.ingest(
        title="空压机维修规范",
        equipment_model="compressor-002",
        content="冷却器堵塞\n\n---PAGE---\n\n排气温度过高",
    )
    return RAGService(kb, llm)


def test_model_failure_degrades_to_facts():
    svc = _make_service(_FailingLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "model_unavailable"
    assert resp.sources
    assert any(s.type == "fact" for s in resp.statements)
    assert any(s.type == "pending" for s in resp.statements)


def test_invalid_citation_is_demoted():
    svc = _make_service(_BadCitationLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "no_answer"
    assert resp.statements[0].type == "pending"
    assert resp.statements[0].source_ids == []


def test_conflicts_and_suggestions_flow_through():
    svc = _make_service(_ConflictingLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.conflicts
    assert resp.conflicts[0].field == "额定排气压力"
    assert resp.verification_suggestions


def test_mock_llm_marks_is_mock_true():
    svc = _make_service(MockLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.is_mock is True
    assert any(s.type == "fact" and s.source_ids for s in resp.statements)


def _http_provider(handler) -> HttpDeviceProvider:
    return HttpDeviceProvider(
        base_url="http://business-api",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _air_compressor_payload(**overrides) -> dict:
    data = {
        "id": "AC-07",
        "name": "螺杆空气压缩机",
        "type": "动力与流体机械",
        "model": "GX11",
        "location": "压缩站 Bay03",
        "state": "attention",
    }
    data.update(overrides)
    return data


def _kb_with_two_models() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb.ingest(
        title="空压机维修规范",
        equipment_model="compressor-002",
        content="概述\n\n---PAGE---\n\n排气温度过高：检查冷却器与油位。",
    )
    kb.ingest(
        title="离心泵维护手册",
        equipment_model="pump-004",
        content="概述\n\n---PAGE---\n\n机械密封泄漏：检查冲洗管线。",
    )
    return kb


def test_end_to_end_device_http_rag_and_grounded_output():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload())

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.sources
    assert {evidence.title for evidence in resp.sources} == {"空压机维修规范"}
    source_ids = {evidence.id for evidence in resp.sources}
    facts = [statement for statement in resp.statements if statement.type == "fact"]
    assert facts
    assert all(statement.source_ids for statement in facts)
    assert all(set(statement.source_ids) <= source_ids for statement in facts)


def test_http_device_outside_static_catalog_is_supported():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload(id="AC-99"))

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose("AC-99", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.sources


def test_device_provider_timeout_degrades_without_evidence():
    def handler(request):
        raise httpx.TimeoutException("timeout")

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "device_unavailable"
    assert resp.sources == []
    assert resp.statements == []


def test_http_device_unknown_model_returns_no_knowledge():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload(model="UNKNOWN"))

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "no_knowledge"
    assert resp.sources == []


def test_http_device_rejects_mismatched_equipment_model():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload())

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose(
        "AC-07", "排气温度过高怎么排查？", equipment_model="pump-004"
    )

    assert resp.status == "model_mismatch"
    assert resp.sources == []


def test_http_device_accepts_device_model_alias():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload())

    svc = RAGService(_kb_with_two_models(), MockLLM(), _http_provider(handler))

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？", equipment_model="GX11")

    assert resp.status == "ok"
    assert resp.sources


def test_mixed_valid_and_invalid_citations_are_not_ok():
    svc = _make_service(_MixedCitationLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "no_answer"
    assert resp.statements[0].type == "fact"
    assert resp.statements[0].source_ids == [resp.sources[0].id]
    assert resp.statements[1].type == "pending"
    assert resp.statements[1].source_ids == []
    assert "无依据事实" not in resp.answer
    assert "混合引用摘要" not in resp.summary


def test_provider_identity_mismatch_is_rejected():
    svc = RAGService(_kb_with_two_models(), MockLLM(), _WrongDeviceProvider())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "device_mismatch"
    assert resp.sources == []
    assert resp.statements == []


class _CapturingLLM(MockLLM):
    name = "mock"

    def __init__(self):
        self.last_device = None

    def answer(self, query, evidences, device=None):
        self.last_device = device
        return super().answer(query, evidences, device=device)


class _BadConflictLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences, device=device)
        result.conflicts = [
            Conflict(
                field="编造冲突",
                sources=[
                    ConflictSource(
                        origin="document", value="编造值", ref="not-in-evidence"
                    )
                ],
            )
        ]
        return result


class _RealLikeLLM(MockLLM):
    is_mock = False
    name = "openai"


def test_device_facts_are_passed_to_llm():
    llm = _CapturingLLM()
    svc = _make_service(llm)

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert llm.last_device is not None
    assert llm.last_device.device_id == "AC-07"
    assert llm.last_device.model == "GX11"


def test_invalid_conflict_document_ref_is_dropped():
    svc = _make_service(_BadConflictLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.conflicts == []


def test_static_provider_is_marked_demo():
    svc = _make_service(MockLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.device_source == "static"
    assert resp.is_demo is True


def test_http_provider_with_real_llm_is_not_demo():
    def handler(request):
        return httpx.Response(200, json=_air_compressor_payload())

    svc = RAGService(
        _kb_with_two_models(), _RealLikeLLM(), _http_provider(handler)
    )

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "ok"
    assert resp.device_source == "http"
    assert resp.is_demo is False
