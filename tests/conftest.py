import pytest

from app.core.device_provider import StaticDeviceProvider
from app.deps import kb, rag
from app.llm.mock import MockLLM


@pytest.fixture(autouse=True)
def reset_kb():
    kb.storage_path = None
    kb.clear()
    rag.llm = MockLLM()
    rag.device_provider = StaticDeviceProvider()
    yield
    rag.device_provider.close()
    kb.clear()
