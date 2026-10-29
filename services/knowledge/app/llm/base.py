from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.schemas.chat import Conflict, Statement, VerificationSuggestion
from app.schemas.document import Evidence

if TYPE_CHECKING:
    from app.core.device_provider import DeviceContext


class LLMError(Exception):
    """模型调用失败（超时、网络、鉴权、解析失败等）。"""


@dataclass
class LLMResult:
    answer: str
    statements: list[Statement]
    summary: str = ""
    conflicts: list[Conflict] = field(default_factory=list)
    verification_suggestions: list[VerificationSuggestion] = field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class BaseLLM(ABC):
    is_mock: bool = True
    name: str = "unknown"

    @abstractmethod
    def answer(
        self,
        query: str,
        evidences: list[Evidence],
        device: DeviceContext | None = None,
    ) -> LLMResult:
        raise NotImplementedError

    def close(self) -> None:
        pass
