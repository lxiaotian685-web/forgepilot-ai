from __future__ import annotations

from app.config import STORAGE_PATH
from app.core.device_provider import build_device_provider
from app.core.store import KnowledgeBase
from app.llm.factory import build_llm
from app.services.rag import RAGService

kb = KnowledgeBase(STORAGE_PATH)
rag = RAGService(kb, build_llm(), build_device_provider())


def get_kb() -> KnowledgeBase:
    return kb


def get_rag() -> RAGService:
    return rag
