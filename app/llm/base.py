from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.chat import Conflict, Statement, VerificationSuggestion
from app.schemas.document import Evidence


class LLMError(Exception):
    """模型调用失败（超时、网络、鉴权、解析失败等）。"""


@dataclass
class LLMResult:
    answer: str
    statements: list[Statement]
    conflicts: list[Conflict] = field(default_factory=list)
    verification_suggestions: list[VerificationSuggestion] = field(default_factory=list)


class BaseLLM(ABC):
    is_mock: bool = True

    @abstractmethod
    def answer(self, query: str, evidences: list[Evidence]) -> LLMResult:
        raise NotImplementedError
