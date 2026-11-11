from app.core.store import KnowledgeBase
from app.llm.mock import MockLLM
from app.schemas.chat import Statement
from app.services.rag import RAGService


class _NoFactLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences, device=device)
        result.answer = "只有推断，没有可核实事实。"
        result.summary = "只有推断。"
        result.statements = [
            Statement(type="inference", text="可能存在问题", source_ids=[])
        ]
        return result


def _versioned_kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb.ingest(
        title="空压机维修规范",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="1.0",
        content="版本一：排气温度过高排查：冷却器、油位。",
    )
    kb.ingest(
        title="空压机维修规范",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="2.0",
        content="版本二：排气温度过高排查：冷却风扇、环境温度。",
    )
    return kb


def test_search_filters_by_document_version():
    kb = _versioned_kb()

    v1 = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="1.0",
    )
    v2 = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="2.0",
    )
    all_versions = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
    )

    assert v1
    assert v2
    assert {result.version for result in v1} == {"1.0"}
    assert {result.version for result in v2} == {"2.0"}
    assert {result.version for result in all_versions} == {"1.0", "2.0"}


def test_version_mismatch_returns_no_evidence():
    kb = _versioned_kb()

    results = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="9.9",
    )

    assert results == []


def test_search_dedupes_identical_chunks_same_version():
    kb = KnowledgeBase()
    content = "重复片段：排气温度过高排查：冷却器、油位。"
    for title in ("重复手册A", "重复手册B"):
        kb.ingest(
            title=title,
            equipment_model="compressor-002",
            organization_id="org-a",
            version="1.0",
            content=content,
        )

    results = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="1.0",
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].snippet == content


def test_search_expands_candidates_until_top_k_unique():
    kb = KnowledgeBase()
    for index in range(20):
        kb.ingest(
            title=f"重复手册{index}",
            equipment_model="compressor-002",
            organization_id="org-a",
            version="1.0",
            content="排气温度过高",
        )
    for index in range(6):
        kb.ingest(
            title=f"不同证据手册{index}",
            equipment_model="compressor-002",
            organization_id="org-a",
            version="1.0",
            content=(
                "排气温度过高时应检查冷却系统并记录运行参数，"
                f"这是第{index}条不同证据说明。"
            ),
        )

    results = kb.search(
        "排气温度过高",
        equipment_model="compressor-002",
        organization_id="org-a",
        version="1.0",
        top_k=5,
    )

    assert len(results) == 5
    snippets = [" ".join(item.snippet.split()) for item in results]
    assert len(set(snippets)) == 5


def test_search_keeps_same_text_across_equipment_models():
    kb = KnowledgeBase()
    content = "排气温度过高排查：冷却器。"
    for model in ("compressor-002", "compressor-003"):
        kb.ingest(
            title=f"{model}手册",
            equipment_model=model,
            organization_id="org-a",
            version="1.0",
            content=content,
        )

    results = kb.search(
        "排气温度过高",
        organization_id="org-a",
        top_k=5,
    )

    assert len(results) == 2
    assert {item.snippet for item in results} == {content}


def test_version_filter_applies_during_diagnosis():
    kb = _versioned_kb()
    svc = RAGService(kb, MockLLM())

    v1 = svc.diagnose(
        "AC-07", "排气温度过高怎么排查？", version="1.0"
    )
    all_versions = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert v1.status == "ok"
    assert v1.sources
    assert {source.version for source in v1.sources} == {"1.0"}
    assert all_versions.sources
    assert {source.version for source in all_versions.sources} == {"1.0", "2.0"}


def test_model_without_grounded_fact_returns_no_answer():
    kb = _versioned_kb()
    svc = RAGService(kb, _NoFactLLM())

    resp = svc.diagnose("AC-07", "排气温度过高怎么排查？")

    assert resp.status == "no_answer"
    assert resp.sources
    assert "证据不足" in resp.summary
    assert all(statement.type != "fact" for statement in resp.statements)
