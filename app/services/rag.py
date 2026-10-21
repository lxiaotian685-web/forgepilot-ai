from __future__ import annotations

from app.core.device_provider import (
    DeviceProvider,
    DeviceProviderError,
    StaticDeviceProvider,
)
from app.core.store import KnowledgeBase
from app.llm.base import BaseLLM, LLMError
from app.schemas.chat import ChatResponse, Statement, VerificationSuggestion
from app.schemas.document import Evidence


class RAGService:
    def __init__(
        self,
        kb: KnowledgeBase,
        llm: BaseLLM,
        device_provider: DeviceProvider | None = None,
        top_k: int = 3,
    ):
        self.kb = kb
        self.llm = llm
        self.device_provider = device_provider or StaticDeviceProvider()
        self.top_k = top_k

    def diagnose(
        self,
        device_id: str,
        question: str,
        equipment_model: str | None = None,
    ) -> ChatResponse:
        try:
            device = self.device_provider.get_device(device_id)
        except DeviceProviderError as exc:
            return self._unavailable(device_id, exc.status, exc.message)

        if device.knowledge_model is None:
            return self._unavailable(
                device_id,
                "no_knowledge",
                f"设备 {device_id} 暂无适用的知识库文档。",
            )

        if equipment_model is not None and equipment_model not in {
            device.knowledge_model,
            device.model,
        }:
            return self._unavailable(
                device_id,
                "model_mismatch",
                f"设备 {device_id} 的型号与传入的型号不一致，已拒绝检索。",
            )

        evidences = self.kb.search(
            question,
            equipment_model=device.knowledge_model,
            top_k=self.top_k,
        )

        if not evidences:
            return ChatResponse(
                device_id=device_id,
                answer="未在知识库中找到相关文档，无法给出有证据的诊断建议。",
                statements=[],
                sources=[],
                is_mock=self.llm.is_mock,
                status="no_answer",
            )

        try:
            result = self.llm.answer(question, evidences)
        except LLMError:
            return self._degraded(device_id, evidences)

        statements, ungrounded = self._validate_sources(result.statements, evidences)

        if ungrounded:
            return ChatResponse(
                device_id=device_id,
                answer=(
                    "模型给出的引用无法在本次检索结果中核实，不能作为有依据的诊断。"
                    "以下内容仅为待人工核验的线索。"
                ),
                summary="模型引用无法核实，仅为待人工核验线索。",
                statements=statements,
                sources=evidences,
                conflicts=result.conflicts,
                verification_suggestions=result.verification_suggestions,
                is_mock=self.llm.is_mock,
                status="no_answer",
            )

        return ChatResponse(
            device_id=device_id,
            answer=result.answer,
            summary=result.summary or result.answer,
            statements=statements,
            sources=evidences,
            conflicts=result.conflicts,
            verification_suggestions=result.verification_suggestions,
            is_mock=self.llm.is_mock,
            status="ok",
        )

    def _unavailable(
        self, device_id: str, status: str, answer: str
    ) -> ChatResponse:
        return ChatResponse(
            device_id=device_id,
            answer=answer,
            statements=[],
            sources=[],
            is_mock=self.llm.is_mock,
            status=status,
        )

    def _degraded(self, device_id: str, evidences: list[Evidence]) -> ChatResponse:
        statements = [self._to_fact(ev) for ev in evidences]
        statements.append(
            Statement(
                type="pending",
                text="模型服务不可用，以上为检索到的文档证据，诊断结论需人工确认。",
                source=None,
                source_ids=[],
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
            summary="模型服务不可用，以下为检索到的文档证据。",
            statements=statements,
            sources=evidences,
            verification_suggestions=[
                VerificationSuggestion(
                    missing_evidence="可用模型服务或人工复核",
                    to_verify="确认以上文档证据是否足以支撑人工诊断结论",
                )
            ],
            is_mock=self.llm.is_mock,
            status="model_unavailable",
        )

    @staticmethod
    def _validate_sources(
        statements: list[Statement], evidences: list[Evidence]
    ) -> tuple[list[Statement], bool]:
        valid = {ev.id for ev in evidences}
        had_fact = False
        grounded_fact = False
        for statement in statements:
            statement.source_ids = list(dict.fromkeys(statement.source_ids))
            if statement.type == "fact":
                had_fact = True
            statement.source_ids = [
                sid for sid in statement.source_ids if sid in valid
            ]
            if statement.type == "fact":
                if statement.source_ids:
                    grounded_fact = True
                else:
                    statement.type = "pending"
        return statements, had_fact and not grounded_fact

    @staticmethod
    def _ref(ev: Evidence) -> str:
        page = ev.page if ev.page is not None else "未知"
        return f"《{ev.title}》第{page}页"

    @staticmethod
    def _to_fact(ev: Evidence) -> Statement:
        return Statement(
            type="fact",
            text=ev.snippet,
            source=RAGService._ref(ev),
            source_ids=[ev.id],
        )
