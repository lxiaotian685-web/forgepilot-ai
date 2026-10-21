from __future__ import annotations

from app.llm.base import BaseLLM, LLMError, LLMResult
from app.schemas.chat import Statement, VerificationSuggestion
from app.schemas.document import Evidence


class MockLLM(BaseLLM):
    is_mock = True

    def answer(self, query: str, evidences: list[Evidence]) -> LLMResult:
        lines = ["基于知识库检索，给出以下模拟诊断建议（请结合现场确认）：", ""]
        statements: list[Statement] = []
        for i, ev in enumerate(evidences, start=1):
            ref = self._ref(ev)
            lines.append(f"{i}. 参考{ref}：{ev.snippet}")
            statements.append(
                Statement(
                    type="fact",
                    text=ev.snippet,
                    source=ref,
                    source_ids=[ev.id],
                )
            )
        statements.append(
            Statement(
                type="inference",
                text="综合以上文档证据，建议从文档列出的最靠前的常见原因开始逐项排查。",
                source=None,
                source_ids=[],
            )
        )
        statements.append(
            Statement(
                type="pending",
                text="本回答为模拟生成，关键参数校验和高风险操作前须人工确认。",
                source=None,
                source_ids=[],
            )
        )
        suggestions = [
            VerificationSuggestion(
                missing_evidence="现场测量数据（温度/振动/压力）与近期检修记录",
                to_verify="核验文档列出的可能原因中哪一项是本次故障主因",
            )
        ]
        return LLMResult(
            answer="\n".join(lines),
            statements=statements,
            verification_suggestions=suggestions,
        )

    @staticmethod
    def _ref(ev: Evidence) -> str:
        page = ev.page if ev.page is not None else "未知"
        return f"《{ev.title}》第{page}页"


class UnavailableLLM(BaseLLM):
    is_mock = True

    def answer(self, query: str, evidences: list[Evidence]) -> LLMResult:
        raise LLMError("模型服务不可用")
