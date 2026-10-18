import pytest

from app.llm.mock import MockLLM
from app.main import kb, rag


@pytest.fixture(autouse=True)
def reset_kb():
    kb.storage_path = None
    kb.clear()
    rag.llm = MockLLM()
    yield
    kb.clear()
