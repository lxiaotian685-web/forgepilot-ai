from __future__ import annotations

from app.config import DEMO_DOCS_DIR, STORAGE_PATH
from app.core.store import KnowledgeBase

DOCS = [
    ("motor_maintenance.txt", "电机维护手册", "motor-001"),
    ("air_compressor.txt", "空压机维修规范", "compressor-002"),
    ("cnc_safety.txt", "数控机床安全操作规范", "cnc-003"),
]


def main() -> None:
    kb = KnowledgeBase(STORAGE_PATH)
    kb.clear()
    for filename, title, model in DOCS:
        path = DEMO_DOCS_DIR / filename
        if not path.exists():
            print(f"跳过（文件不存在）: {path}")
            continue
        content = path.read_text(encoding="utf-8")
        doc, chunks = kb.ingest(
            title=title,
            equipment_model=model,
            content=content,
            source=filename,
        )
        print(f"已入库: {title} ({model}) -> {doc.page_count} 页 / {len(chunks)} 分块")
    kb.save()
    print(f"知识库已保存: {STORAGE_PATH}")


if __name__ == "__main__":
    main()
