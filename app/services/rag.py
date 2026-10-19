from __future__ import annotations

from app.core.devices import resolve_equipment_model
from app.core.store import KnowledgeBase
from app.llm.base import BaseLLM
from app.schemas.chat import ChatResponse, Statement
from app.schemas.document import Evidence


class RAGService:
    def __init__(self, kb: KnowledgeBase, llm: BaseLLM, top_k: int = 3):
        self.kb = kb
        self.llm = llm
        self.top_k = top_k

    def diagnose(
        self,
        device_id: str,
        question: str,
        equipment_model: str | None = None,
    ) -> ChatResponse:
        model, status = resolve_equipment_model(device_id, equipment_model)
        if model is None:
            if status == "device_not_found":
                answer = f"未找到设备 {device_id} 对应的设备型号，无法检索知识库。"
            else:
                answer = f"设备 {device_id} 暂无适用的知识库文档。"
            return ChatResponse(
                device_id=device_id,
                answer=answer,
                statements=[],
                sources=[],
                is_mock=True,
                status=status,
            )

        evidences = self.kb.search(question, equipment_model=model, top_k=self.top_k)

        if not evidences:
            return ChatResponse(
                device_id=device_id,
                answer="未在知识库中找到相关文档，无法给出有证据的诊断建议。",
                statements=[],
                sources=[],
                is_mock=True,
                status="no_answer",
            )

        if not self.llm.available:
            statements = [self._to_fact(ev) for ev in evidences]
            statements.append(
                Statement(
                    type="pending",
                    text="模型服务不可用，以上为检索到的文档证据，诊断结论需人工确认。",
                    source=None,
                )
            )
            lines = [
                "模型服务当前不可用，无法生成诊断结论。以下为检索到的相关文档片段，仅供人工参考：",
                "",
            ]
            for i, ev in enumerate(evidences, start=1):
                lines.append(f"{i}. {self._ref(ev)}：{ev.snippet}")
            return ChatResponse(
                device_id=device_id,
                answer="\n".join(lines),
                statements=statements,
                sources=evidences,
                is_mock=True,
                status="model_unavailable",
            )

        answer, statements = self.llm.answer(question, evidences)
        return ChatResponse(
            device_id=device_id,
            answer=answer,
            statements=statements,
            sources=evidences,
            is_mock=True,
            status="ok",
        )

    @staticmethod
    def _ref(ev: Evidence) -> str:
        return f"《{ev.title}》第{ev.page}页"

    @staticmethod
    def _to_fact(ev: Evidence) -> Statement:
        return Statement(
            type="fact",
            text=ev.snippet,
            source=RAGService._ref(ev),
        )
