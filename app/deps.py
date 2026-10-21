from __future__ import annotations

from app.config import STORAGE_PATH
from app.core.store import KnowledgeBase
from app.llm.factory import build_llm
from app.services.rag import RAGService

kb = KnowledgeBase(STORAGE_PATH)
rag = RAGService(kb, build_llm())


def get_kb() -> KnowledgeBase:
    return kb


def get_rag() -> RAGService:
    return rag
