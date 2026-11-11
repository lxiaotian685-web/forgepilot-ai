from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

from app.config import default_organization_id
from app.core.demo import ingest_demo_docs
from app.core.device_provider import DeviceAuth
from app.core.store import KnowledgeBase
from app.llm.base import LLMError
from app.llm.mock import MockLLM
from app.llm.openai import OpenAILLM
from app.schemas.chat import Statement
from app.services.rag import RAGService

ROOT = Path(__file__).resolve().parent.parent
EVAL_PATH = ROOT / "evaluation" / "evidence_quality.json"
MIN_HIT_RATE = 1.0
MIN_CITATION_RATE = 1.0
MIN_NO_MATCH_RATE = 1.0


class _NoFactLLM(MockLLM):
    def answer(self, query, evidences, device=None):
        result = super().answer(query, evidences, device=device)
        result.answer = "只有推断，没有可核实事实。"
        result.summary = "只有推断。"
        result.statements = [
            Statement(type="inference", text="可能存在问题", source_ids=[])
        ]
        return result


class _TimeoutLLM(MockLLM):
    is_mock = False
    name = "timeout"

    def answer(self, query, evidences, device=None):
        raise LLMError("模型调用超时")


def _auth_fail_llm() -> OpenAILLM:
    def handler(request):
        return httpx.Response(
            401, json={"error": {"message": "unauthorized"}}
        )

    return OpenAILLM(
        api_key="test",
        base_url="http://model",
        model="test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _build_kb() -> tuple[KnowledgeBase, str]:
    kb = KnowledgeBase()
    organization_id = default_organization_id()
    ingest_demo_docs(kb, organization_id=organization_id)
    for title, version, content in (
        ("质量测试手册", "1.0", "重复切片：排气温度过高排查：冷却器。"),
        ("质量测试手册副本", "1.0", "重复切片：排气温度过高排查：冷却器。"),
        ("质量测试手册", "2.0", "重复切片：排气温度过高排查：冷却风扇。"),
    ):
        kb.ingest(
            title=title,
            equipment_model="quality-001",
            organization_id=organization_id,
            version=version,
            content=content,
        )
    return kb, organization_id


def _retrieval_hits(
    kb: KnowledgeBase, organization_id: str, cases: list[dict]
) -> tuple[int, list[str]]:
    hits = 0
    failures: list[str] = []
    for case in cases:
        results = kb.search(
            case["question"],
            equipment_model=case["equipment_model"],
            version=case["version"],
            top_k=3,
            organization_id=organization_id,
        )
        matched = any(
            item.title == case["expected_title"]
            and item.page == case["expected_page"]
            for item in results
        )
        if matched:
            hits += 1
        else:
            failures.append(case["id"])
    return hits, failures


def _citation_consistency(
    kb: KnowledgeBase, organization_id: str, cases: list[dict]
) -> tuple[int, list[str]]:
    service = RAGService(kb, MockLLM())
    consistent = 0
    failures: list[str] = []
    for case in cases:
        response = service.diagnose(
            case["device_id"],
            case["question"],
            version=case["version"],
            auth=DeviceAuth(organization_id=organization_id),
        )
        source_ids = {source.id for source in response.sources}
        facts = [
            statement
            for statement in response.statements
            if statement.type == "fact"
        ]
        fields_ok = all(
            source.id
            and source.document_id
            and source.version
            and source.title
            and source.snippet
            and source.score is not None
            and source.chunk_index is not None
            for source in response.sources
        )
        facts_ok = bool(facts) and all(
            statement.source_ids
            and statement.source
            and set(statement.source_ids) <= source_ids
            for statement in facts
        )
        if (
            response.status == "ok"
            and response.sources
            and fields_ok
            and facts_ok
        ):
            consistent += 1
        else:
            failures.append(case["id"])
    return consistent, failures


def _no_match_correct(
    kb: KnowledgeBase, organization_id: str, cases: list[dict]
) -> tuple[int, list[str]]:
    correct = 0
    failures: list[str] = []
    for case in cases:
        results = kb.search(
            case["question"],
            equipment_model=case["equipment_model"],
            version=case["version"],
            top_k=3,
            organization_id=organization_id,
        )
        if results:
            failures.append(case["id"])
        else:
            correct += 1
    return correct, failures


def _duplicate_count(kb: KnowledgeBase, organization_id: str) -> tuple[int, int]:
    results = kb.search(
        "重复切片",
        equipment_model="quality-001",
        version="1.0",
        top_k=5,
        organization_id=organization_id,
    )
    normalized = [" ".join(item.snippet.split()) for item in results]
    return len(results), len(normalized) - len(set(normalized))


def _version_filter_ok(kb: KnowledgeBase, organization_id: str) -> bool:
    v1 = kb.search(
        "排气温度过高",
        equipment_model="quality-001",
        version="1.0",
        top_k=5,
        organization_id=organization_id,
    )
    v2 = kb.search(
        "排气温度过高",
        equipment_model="quality-001",
        version="2.0",
        top_k=5,
        organization_id=organization_id,
    )
    both = kb.search(
        "排气温度过高",
        equipment_model="quality-001",
        top_k=5,
        organization_id=organization_id,
    )
    return (
        bool(v1)
        and bool(v2)
        and {item.version for item in v1} == {"1.0"}
        and {item.version for item in v2} == {"2.0"}
        and {item.version for item in both} == {"1.0", "2.0"}
    )


def _degradation_checks(
    kb: KnowledgeBase, organization_id: str, case: dict
) -> tuple[bool, bool, bool]:
    auth = DeviceAuth(organization_id=organization_id)

    insufficient = RAGService(kb, _NoFactLLM()).diagnose(
        case["device_id"],
        case["question"],
        version=case["version"],
        auth=auth,
    )
    timeout = RAGService(kb, _TimeoutLLM()).diagnose(
        case["device_id"],
        case["question"],
        version=case["version"],
        auth=auth,
    )
    auth_fail = RAGService(kb, _auth_fail_llm()).diagnose(
        case["device_id"],
        case["question"],
        version=case["version"],
        auth=auth,
    )

    return (
        insufficient.status == "no_answer" and bool(insufficient.sources),
        timeout.status == "model_unavailable" and bool(timeout.sources),
        auth_fail.status == "model_unavailable" and bool(auth_fail.sources),
    )


def main() -> int:
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    retrieval_cases = data["retrieval_cases"]
    no_match_cases = data["no_match_cases"]
    insufficient_cases = data["insufficient_cases"]
    kb, organization_id = _build_kb()

    hit_count, hit_failures = _retrieval_hits(
        kb, organization_id, retrieval_cases
    )
    citation_count, citation_failures = _citation_consistency(
        kb, organization_id, retrieval_cases
    )
    no_match_count, no_match_failures = _no_match_correct(
        kb, organization_id, no_match_cases
    )
    dedupe_total, duplicate_count = _duplicate_count(kb, organization_id)
    version_ok = _version_filter_ok(kb, organization_id)
    insufficient_ok, timeout_ok, auth_ok = _degradation_checks(
        kb, organization_id, insufficient_cases[0]
    )

    hit_rate = hit_count / len(retrieval_cases)
    citation_rate = citation_count / len(retrieval_cases)
    no_match_rate = no_match_count / len(no_match_cases)

    print(f"检索命中: {hit_count}/{len(retrieval_cases)} = {hit_rate:.1%}")
    print(
        f"引用一致性: {citation_count}/{len(retrieval_cases)} = "
        f"{citation_rate:.1%}"
    )
    print(
        f"无匹配资料: {no_match_count}/{len(no_match_cases)} = "
        f"{no_match_rate:.1%}"
    )
    print(f"重复切片: {duplicate_count} 条（返回 {dedupe_total} 条）")
    print(f"版本过滤: {'PASS' if version_ok else 'FAIL'}")
    print(f"证据不足降级: {'PASS' if insufficient_ok else 'FAIL'}")
    print(f"模型超时降级: {'PASS' if timeout_ok else 'FAIL'}")
    print(f"模型鉴权失败降级: {'PASS' if auth_ok else 'FAIL'}")

    failures: list[str] = []
    if hit_rate < MIN_HIT_RATE:
        failures.append(f"检索命中 {hit_failures}")
    if citation_rate < MIN_CITATION_RATE:
        failures.append(f"引用一致性 {citation_failures}")
    if no_match_rate < MIN_NO_MATCH_RATE:
        failures.append(f"无匹配资料 {no_match_failures}")
    if duplicate_count:
        failures.append("存在重复切片")
    if not version_ok:
        failures.append("版本过滤")
    if not insufficient_ok:
        failures.append("证据不足降级")
    if not timeout_ok:
        failures.append("模型超时降级")
    if not auth_ok:
        failures.append("模型鉴权失败降级")
    if failures:
        raise SystemExit("证据质量评测未通过: " + "；".join(failures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
