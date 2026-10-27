from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    device_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


class ChatResponse(BaseModel):
    device_id: str
    answer: str
    sources: list[str]
    is_mock: bool
