from __future__ import annotations

import os
import sys
from typing import Any

import httpx

REQUIRED_SOURCE_FIELDS = (
    "id",
    "document_id",
    "version",
    "title",
    "chunk_index",
    "snippet",
    "score",
)


def check_health(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "ok":
        errors.append("health: status 不是 ok")
    if payload.get("llm_provider") != "openai":
        errors.append("health: llm_provider 不是 openai（当前不是真实模型）")
    if payload.get("device_provider") != "http":
        errors.append("health: device_provider 不是 http（当前不是真实设备事实）")
    return errors


def check_chat(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "ok":
        errors.append(f"chat: status={payload.get('status')}，不是 ok")
    if payload.get("is_mock") is not False:
        errors.append("chat: is_mock 不是 false")
    if payload.get("is_demo") is not False:
        errors.append("chat: is_demo 不是 false")

    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("chat: sources 为空")
        return errors

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"chat: sources[{index}] 不是对象")
            continue
        for field in REQUIRED_SOURCE_FIELDS:
            if source.get(field) in (None, ""):
                errors.append(f"chat: sources[{index}].{field} 缺失")
        if "page" not in source:
            errors.append(
                f"chat: sources[{index}].page 缺失（未知页码应显式 null）"
            )
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id:
            source_ids.add(source_id)

    statements = payload.get("statements")
    if not isinstance(statements, list):
        errors.append("chat: statements 不是列表")
        return errors

    facts = [
        item
        for item in statements
        if isinstance(item, dict) and item.get("type") == "fact"
    ]
    if not facts:
        errors.append("chat: 没有 fact 陈述")
    for index, fact in enumerate(facts):
        ids = fact.get("source_ids")
        if not isinstance(ids, list) or not ids:
            errors.append(f"chat: fact[{index}] 没有 source_ids")
            continue
        missing = [source_id for source_id in ids if source_id not in source_ids]
        if missing:
            errors.append(f"chat: fact[{index}] 引用了未知证据 {missing}")
    return errors


def check_no_answer(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "no_answer":
        errors.append(f"no-answer: status={payload.get('status')}，不是 no_answer")
    if payload.get("sources"):
        errors.append("no-answer: 不应返回证据")
    return errors


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    organization = os.getenv("C_ORGANIZATION_ID") or os.getenv(
        "C_DEFAULT_ORGANIZATION_ID"
    )
    if organization:
        headers["X-Organization-Id"] = organization
    user = os.getenv("C_USER_ID")
    if user:
        headers["X-User-Id"] = user
    token = os.getenv("C_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _post_chat(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    device_id: str,
    question: str,
) -> dict[str, Any]:
    response = client.post(
        f"{base_url}/api/v1/chat",
        headers=headers,
        json={"device_id": device_id, "question": question},
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"chat HTTP {response.status_code}: 响应不是 JSON"
        ) from exc
    if response.status_code >= 500:
        raise RuntimeError(f"chat HTTP {response.status_code}: {payload}")
    return payload


def main() -> int:
    base_url = os.getenv(
        "C_API_BASE_URL", "http://127.0.0.1:8002"
    ).rstrip("/")
    headers = _headers()
    device_id = os.getenv("C_DEVICE_ID", "AC-07")
    question = os.getenv("C_QUESTION", "排气温度过高怎么排查？")
    no_answer_question = os.getenv(
        "C_NO_ANSWER_QUESTION", "锅炉汽包水位如何调节？"
    )

    errors: list[str] = []
    try:
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            health_response = client.get(f"{base_url}/health")
            health_response.raise_for_status()
            health = health_response.json()
            errors.extend(check_health(health))

            chat = _post_chat(
                client, base_url, headers, device_id, question
            )
            errors.extend(check_chat(chat))

            no_answer = _post_chat(
                client,
                base_url,
                headers,
                device_id,
                no_answer_question,
            )
            errors.extend(check_no_answer(no_answer))
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    if errors:
        print("真实 RAG 验收失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    facts = [
        item
        for item in chat.get("statements", [])
        if item.get("type") == "fact"
    ]
    print("真实 RAG 验收通过：")
    print(f"- llm_provider={health.get('llm_provider')}")
    print(f"- device_provider={health.get('device_provider')}")
    print(
        "- status="
        f"{chat.get('status')} is_mock={chat.get('is_mock')} "
        f"is_demo={chat.get('is_demo')}"
    )
    print(f"- sources={len(chat.get('sources', []))} fact={len(facts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
