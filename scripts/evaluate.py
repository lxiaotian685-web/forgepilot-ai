from __future__ import annotations

import json
from pathlib import Path

from app.core.demo import ingest_demo_docs
from app.core.store import KnowledgeBase

ROOT = Path(__file__).resolve().parent.parent


def build_kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    ingest_demo_docs(kb)
    return kb


def main() -> None:
    eval_path = ROOT / "evaluation" / "eval_set.json"
    questions = json.loads(eval_path.read_text(encoding="utf-8"))["questions"]
    kb = build_kb()

    answerable = 0
    hits = 0
    page_hits = 0
    no_answer_total = 0
    no_answer_correct = 0

    for q in questions:
        results = kb.search(
            q["question"], equipment_model=q.get("equipment_model"), top_k=3
        )
        if q.get("has_answer", True):
            answerable += 1
            titles = [r.title for r in results]
            if q["expected_document"] in titles:
                hits += 1
            if any(
                r.title == q["expected_document"] and r.page == q["expected_page"]
                for r in results
            ):
                page_hits += 1
        else:
            no_answer_total += 1
            if not results:
                no_answer_correct += 1

    print(f"可答问题数: {answerable}")
    print(f"命中率 (期望文档进入 top3): {hits}/{answerable} = {hits / answerable:.1%}")
    print(
        f"引用准确率 (期望页码进入 top3): {page_hits}/{answerable} = "
        f"{page_hits / answerable:.1%}"
    )
    print(
        f"无答案准确率: {no_answer_correct}/{no_answer_total} = "
        f"{no_answer_correct / no_answer_total:.1%}"
    )


if __name__ == "__main__":
    main()
