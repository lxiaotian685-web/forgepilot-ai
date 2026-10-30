from __future__ import annotations

from app.core.device_provider import (
    DeviceAuth,
    DeviceProvider,
    DeviceProviderError,
    StaticDeviceProvider,
)
from app.core.store import KnowledgeBase
from app.llm.base import BaseLLM, LLMError
from app.schemas.chat import (
    ChatResponse,
    Conflict,
    DiagnosisStatus,
    Statement,
    VerificationSuggestion,
)
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
        auth: DeviceAuth | None = None,
    ) -> ChatResponse:
        try:
            device = self.device_provider.get_device(device_id, auth=auth)
        except DeviceProviderError as exc:
            return self._unavailable(device_id, exc.status, exc.message)

        if device.device_id != device_id:
            return self._unavailable(
                device_id,
                "device_mismatch",
                f"设备服务返回的设备编号 {device.device_id} 与请求 {device_id} "
                "不一致，已拒绝使用。",
            )

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

        retrieval_query = question
        for phrase, terms in {
            "发烫": "温度过高 冷却 散热", "很热": "温度过高 冷却",
            "抖": "振动 轴承", "响": "异响 振动 轴承",
            "漏水": "泄漏 机械密封", "漏油": "泄漏 润滑 密封",
            "没劲": "压力不足 负载", "不转": "启动 电机 故障",
        }.items():
            if phrase in question:
                retrieval_query += " " + terms
        evidences = self.kb.search(
            retrieval_query,
            equipment_model=device.knowledge_model,
            top_k=self.top_k,
            organization_id=auth.organization_id if auth else None,
        )

        if not evidences:
            return self._respond(
                device_id,
                "no_answer",
                answer="未在知识库中找到相关文档，无法给出有证据的诊断建议。",
                statements=[],
                sources=[],
            )

        try:
            result = self.llm.answer(question, evidences, device=device)
        except LLMError as exc:
            response = self._degraded(device_id, evidences)
            response.answer = f"本次诊断未完成：{exc}。\n" + response.answer
            return response

        statements, has_ungrounded_fact = self._validate_sources(
            result.statements, evidences
        )
        conflicts = self._validate_conflicts(result.conflicts, evidences)

        if has_ungrounded_fact:
            return self._respond(
                device_id,
                "no_answer",
                answer=(
                    "模型给出的部分事实引用无法在本次检索结果中核实，"
                    "不能作为有依据的诊断。以下仅保留可核实事实，"
                    "其余内容已标记为待人工核验。"
                ),
                summary="模型存在无法核实的引用，结论不可直接采用。",
                statements=statements,
                sources=evidences,
                conflicts=conflicts,
                verification_suggestions=result.verification_suggestions,
            )

        return self._respond(
            device_id,
            "ok",
            answer=result.answer,
            summary=result.summary or result.answer,
            statements=statements,
            sources=evidences,
            conflicts=conflicts,
            verification_suggestions=result.verification_suggestions,
            model_provider=result.provider,
            model_name=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        )

    def _respond(
        self,
        device_id: str,
        status: DiagnosisStatus,
        **fields,
    ) -> ChatResponse:
        device_source = getattr(self.device_provider, "source", "unknown")
        fields.setdefault("model_provider", getattr(self.llm, "name", "unknown"))
        fields.setdefault("model_name", getattr(self.llm, "name", "unknown"))
        return ChatResponse(
            device_id=device_id,
            status=status,
            is_mock=self.llm.is_mock,
            device_source=device_source,
            is_demo=self.llm.is_mock or device_source != "http",
            **fields,
        )

    def _unavailable(
        self, device_id: str, status: DiagnosisStatus, answer: str
    ) -> ChatResponse:
        return self._respond(
            device_id,
            status,
            answer=answer,
            statements=[],
            sources=[],
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
        return self._respond(
            device_id,
            "model_unavailable",
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
        )

    @staticmethod
    def _validate_sources(
        statements: list[Statement], evidences: list[Evidence]
    ) -> tuple[list[Statement], bool]:
        evidence_by_id = {ev.id: ev for ev in evidences}
        has_ungrounded_fact = False
        for statement in statements:
            statement.source_ids = list(dict.fromkeys(statement.source_ids))
            statement.source_ids = [
                sid for sid in statement.source_ids if sid in evidence_by_id
            ]
            if statement.type == "fact" and not statement.source_ids:
                statement.type = "pending"
                has_ungrounded_fact = True
            if statement.type == "fact":
                statement.source = RAGService._ref(
                    evidence_by_id[statement.source_ids[0]]
                )
            else:
                statement.source = None
        return statements, has_ungrounded_fact

    @staticmethod
    def _validate_conflicts(
        conflicts: list[Conflict], evidences: list[Evidence]
    ) -> list[Conflict]:
        valid = {ev.id for ev in evidences}
        cleaned: list[Conflict] = []
        for conflict in conflicts:
            conflict.sources = [
                source
                for source in conflict.sources
                if source.origin != "document"
                or not source.ref
                or source.ref in valid
            ]
            if conflict.sources:
                cleaned.append(conflict)
        return cleaned

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
