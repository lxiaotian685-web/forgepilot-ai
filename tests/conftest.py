import pytest

from app.core.device_provider import StaticDeviceProvider
from app.deps import kb, rag
from app.llm.mock import MockLLM
from app.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_kb(monkeypatch):
    monkeypatch.setenv("C_REQUIRE_AUTH", "false")
    monkeypatch.setenv("C_ENABLE_INGEST", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEVICE_PROVIDER", "static")
    kb.storage_path = None
    kb.clear()
    rag.llm = MockLLM()
    rag.device_provider = StaticDeviceProvider()
    limiter.clear()
    yield
    rag.device_provider.close()
    kb.clear()
