from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_mock_response():
    response = client.post(
        "/api/v1/chat",
        json={
            "device_id": "motor-001",
            "question": "电机温度过高应该检查什么？",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "device_id": "motor-001",
        "answer": "这是第 1 周的模拟诊断回答。",
        "sources": [],
        "is_mock": True,
    }


def test_chat_rejects_missing_question():
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "motor-001"},
    )

    assert response.status_code == 422


def test_chat_rejects_missing_device_id():
    response = client.post(
        "/api/v1/chat",
        json={"question": "电机温度过高应该检查什么？"},
    )

    assert response.status_code == 422


def test_chat_rejects_empty_question():
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "motor-001", "question": ""},
    )

    assert response.status_code == 422


def test_chat_rejects_empty_device_id():
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "", "question": "电机温度过高怎么办？"},
    )

    assert response.status_code == 422
