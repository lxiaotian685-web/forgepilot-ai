from __future__ import annotations

from app.config import STORAGE_PATH
from app.core.demo import ingest_demo_docs
from app.core.store import KnowledgeBase


def main() -> None:
    kb = KnowledgeBase(STORAGE_PATH)
    kb.clear()
    count = ingest_demo_docs(kb)
    print(f"已入库 {count} 份演示文档")
    print(f"知识库保存路径: {STORAGE_PATH}")


if __name__ == "__main__":
    main()
