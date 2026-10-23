from __future__ import annotations

import json
import os
from pathlib import Path

from app.config import default_organization_id
from app.core.demo import ingest_demo_docs
from app.core.store import KnowledgeBase

ROOT = Path(__file__).resolve().parent.parent

MIN_HIT_RATE = float(os.getenv("EVAL_MIN_HIT_RATE", "0.90"))
MIN_PAGE_RATE = float(os.getenv("EVAL_MIN_PAGE_RATE", "0.80"))
MIN_NO_ANSWER_RATE = float(os.getenv("EVAL_MIN_NO_ANSWER_RATE", "0.90"))


def build_kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    ingest_demo_docs(kb, organization_id=default_organization_id())
    return kb


def main() -> None:
    eval_path = ROOT / "evaluation" / "eval_set.json"
    questions = json.loads(eval_path.read_text(encoding="utf-8"))["questions"]
    kb = build_kb()
    organization_id = default_organization_id()

    answerable = 0
    hits = 0
    page_hits = 0
    no_answer_total = 0
    no_answer_correct = 0

    for q in questions:
        results = kb.search(
            q["question"],
            equipment_model=q.get("equipment_model"),
            top_k=3,
            organization_id=organization_id,
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

    hit_rate = hits / answerable if answerable else 0.0
    page_rate = page_hits / answerable if answerable else 0.0
    no_answer_rate = (
        no_answer_correct / no_answer_total if no_answer_total else 1.0
    )

    print(f"可答问题数: {answerable}")
    print(f"命中率 (期望文档进入 top3): {hits}/{answerable} = {hit_rate:.1%}")
    print(f"引用准确率 (期望页码进入 top3): {page_hits}/{answerable} = {page_rate:.1%}")
    print(
        f"无答案准确率: {no_answer_correct}/{no_answer_total} = "
        f"{no_answer_rate:.1%}"
    )

    failures: list[str] = []
    if hit_rate < MIN_HIT_RATE:
        failures.append(f"命中率低于 {MIN_HIT_RATE:.0%}")
    if page_rate < MIN_PAGE_RATE:
        failures.append(f"引用准确率低于 {MIN_PAGE_RATE:.0%}")
    if no_answer_rate < MIN_NO_ANSWER_RATE:
        failures.append(f"无答案准确率低于 {MIN_NO_ANSWER_RATE:.0%}")
    if failures:
        raise SystemExit("RAG 评测未达标: " + "；".join(failures))


if __name__ == "__main__":
    main()
