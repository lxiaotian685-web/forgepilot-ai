from fastapi.testclient import TestClient

from app.llm.mock import UnavailableLLM
from app.main import app, rag

client = TestClient(app)

MOTOR_CONTENT = "概述\n\n---PAGE---\n\n温度过高检查：散热风扇、通风道。"


def _ingest_motor():
    return client.post(
        "/api/v1/documents/ingest",
        json={
            "title": "电机维护手册",
            "equipment_model": "motor-001",
            "content": MOTOR_CONTENT,
        },
    )


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_document():
    response = _ingest_motor()

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "电机维护手册"
    assert body["page_count"] == 2
    assert body["chunk_count"] >= 2


def test_search_returns_evidence():
    _ingest_motor()
    response = client.post(
        "/api/v1/search",
        json={"query": "温度过高", "equipment_model": "motor-001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    result = body["results"][0]
    assert result["title"] == "电机维护手册"
    assert result["page"] >= 1
    assert result["snippet"]
    assert result["score"] > 0


def test_chat_returns_answer_with_sources():
    _ingest_motor()
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "AC-07", "question": "温度过高应该检查什么？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["is_mock"] is True
    assert body["sources"]
    assert body["sources"][0]["title"] == "电机维护手册"
    types = {s["type"] for s in body["statements"]}
    assert "fact" in types
    assert "inference" in types
    assert "pending" in types
    assert any(s["type"] == "fact" and s["source"] for s in body["statements"])


def test_chat_unknown_device_returns_not_found():
    _ingest_motor()
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "UNKNOWN-99", "question": "温度过高应该检查什么？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "device_not_found"
    assert body["sources"] == []


def test_chat_no_answer_when_kb_empty():
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "AC-07", "question": "锅炉水位怎么处理？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_answer"
    assert body["sources"] == []


def test_chat_model_unavailable_returns_evidence():
    _ingest_motor()
    rag.llm = UnavailableLLM()
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "AC-07", "question": "温度过高应该检查什么？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "model_unavailable"
    assert body["sources"]
    assert any(s["type"] == "fact" for s in body["statements"])
    assert any(s["type"] == "pending" for s in body["statements"])


def test_chat_rejects_missing_question():
    response = client.post("/api/v1/chat", json={"device_id": "AC-07"})

    assert response.status_code == 422


def test_chat_rejects_missing_device_id():
    response = client.post("/api/v1/chat", json={"question": "电机温度过高应该检查什么？"})

    assert response.status_code == 422


def test_chat_rejects_empty_question():
    response = client.post(
        "/api/v1/chat", json={"device_id": "AC-07", "question": ""}
    )

    assert response.status_code == 422


def test_chat_rejects_empty_device_id():
    response = client.post(
        "/api/v1/chat", json={"device_id": "", "question": "电机温度过高怎么办？"}
    )

    assert response.status_code == 422
