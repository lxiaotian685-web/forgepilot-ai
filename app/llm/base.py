from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.chat import Statement
from app.schemas.document import Evidence


class BaseLLM(ABC):
    available: bool = True

    @abstractmethod
    def answer(
        self, query: str, evidences: list[Evidence]
    ) -> tuple[str, list[Statement]]:
        raise NotImplementedError
