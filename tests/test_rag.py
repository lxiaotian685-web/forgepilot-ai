from app.core.store import KnowledgeBase
from app.llm.base import LLMError
from app.llm.mock import MockLLM
from app.schemas.chat import Conflict, ConflictSource, Statement
from app.services.rag import RAGService


class _FailingLLM(MockLLM):
    def answer(self, query, evidences):
        raise LLMError("boom")


class _BadCitationLLM(MockLLM):
    def answer(self, query, evidences):
        result = super().answer(query, evidences)
        result.statements = [
            Statement(type="fact", text="x", source=None, source_ids=["not-in-evidence"])
        ]
        return result


class _ConflictingLLM(MockLLM):
    def answer(self, query, evidences):
        result = super().answer(query, evidences)
        result.conflicts = [
            Conflict(
                field="额定排气压力",
                sources=[
                    ConflictSource(origin="device_record", value="0.8 MPa"),
                    ConflictSource(
                        origin="document", value="0.7 MPa", ref="a@v1.0#p1c0"
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

    assert resp.status == "ok"
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
