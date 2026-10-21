from __future__ import annotations

from app.config import STORAGE_PATH
from app.core.store import KnowledgeBase
from app.llm.mock import MockLLM
from app.services.rag import RAGService

kb = KnowledgeBase(STORAGE_PATH)
rag = RAGService(kb, MockLLM())


def get_kb() -> KnowledgeBase:
    return kb


def get_rag() -> RAGService:
    return rag
