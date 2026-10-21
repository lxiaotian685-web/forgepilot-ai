import pytest

from app.deps import kb, rag
from app.llm.mock import MockLLM


@pytest.fixture(autouse=True)
def reset_kb():
    kb.storage_path = None
    kb.clear()
    rag.llm = MockLLM()
    yield
    kb.clear()
