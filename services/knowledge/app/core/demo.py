from __future__ import annotations

from app.config import DEMO_DOCS_DIR, default_organization_id
from app.core.store import KnowledgeBase

DEMO_DOCS = [
    ("air_compressor.txt", "空压机维修规范", "compressor-002"),
    ("centrifugal_pump.txt", "离心泵维护手册", "pump-004"),
    ("cnc_safety.txt", "数控机床安全操作规范", "cnc-003"),
]


def ingest_demo_docs(kb: KnowledgeBase, organization_id: str | None = None) -> int:
    organization_id = organization_id or default_organization_id()
    existing = {
        (doc.title, doc.equipment_model, doc.organization_id)
        for doc in kb.list_documents(organization_id=organization_id, limit=10_000)
    }
    count = 0
    for filename, title, model in DEMO_DOCS:
        path = DEMO_DOCS_DIR / filename
        if not path.exists():
            continue
        if (title, model, organization_id) in existing:
            continue
        content = path.read_text(encoding="utf-8")
        kb.ingest(
            title=title,
            equipment_model=model,
            organization_id=organization_id,
            content=content,
            source=filename,
        )
        count += 1
    return count


def ensure_demo_documents(kb: KnowledgeBase) -> int:
    kb.load()
    organization_id = default_organization_id()
    if kb.list_documents(organization_id=organization_id, limit=1):
        return 0
    return ingest_demo_docs(kb, organization_id=organization_id)
