from __future__ import annotations

from app.llm.base import BaseLLM
from app.schemas.chat import Statement
from app.schemas.document import Evidence


class MockLLM(BaseLLM):
    available = True

    def answer(
        self, query: str, evidences: list[Evidence]
    ) -> tuple[str, list[Statement]]:
        lines = ["基于知识库检索，给出以下模拟诊断建议（请结合现场确认）：", ""]
        statements: list[Statement] = []
        for i, ev in enumerate(evidences, start=1):
            ref = f"《{ev.title}》第{ev.page}页"
            lines.append(f"{i}. 参考{ref}：{ev.snippet}")
            statements.append(Statement(type="fact", text=ev.snippet, source=ref))
        statements.append(
            Statement(
                type="inference",
                text="综合以上文档证据，建议从文档列出的最靠前的常见原因开始逐项排查。",
                source=None,
            )
        )
        statements.append(
            Statement(
                type="pending",
                text="本回答为模拟生成，关键参数校验和高风险操作前须人工确认。",
                source=None,
            )
        )
        return "\n".join(lines), statements


class UnavailableLLM(BaseLLM):
    available = False

    def answer(
        self, query: str, evidences: list[Evidence]
    ) -> tuple[str, list[Statement]]:
        raise RuntimeError("模型服务不可用")
