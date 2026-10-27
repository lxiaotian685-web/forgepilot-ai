from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diagnosis_is_not_served_by_business_api():
    response = client.post(
        "/api/v1/chat",
        json={"device_id": "AC-07", "question": "温度情况如何？"},
    )
    assert response.status_code == 404
