from __future__ import annotations

from app.config import DEMO_DOCS_DIR
from app.core.store import KnowledgeBase

DEMO_DOCS = [
    ("air_compressor.txt", "空压机维修规范", "compressor-002"),
    ("centrifugal_pump.txt", "离心泵维护手册", "pump-004"),
    ("cnc_safety.txt", "数控机床安全操作规范", "cnc-003"),
]


def ingest_demo_docs(kb: KnowledgeBase) -> int:
    count = 0
    for filename, title, model in DEMO_DOCS:
        path = DEMO_DOCS_DIR / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        kb.ingest(title=title, equipment_model=model, content=content, source=filename)
        count += 1
    return count


def ensure_demo_documents(kb: KnowledgeBase) -> int:
    kb.load()
    if kb.list_documents():
        return 0
    return ingest_demo_docs(kb)
