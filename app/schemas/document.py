from pydantic import BaseModel, Field, field_validator

MAX_TITLE_LENGTH = 200
MAX_EQUIPMENT_MODEL_LENGTH = 100
MAX_CONTENT_LENGTH = 200_000
MAX_VERSION_LENGTH = 50
MAX_SOURCE_LENGTH = 500
MAX_QUERY_LENGTH = 2_000


class Document(BaseModel):
    id: str
    title: str
    equipment_model: str
    organization_id: str = "demo-org"
    version: str = "1.0"
    source: str = ""
    page_count: int = 0


class Chunk(BaseModel):
    id: str
    document_id: str
    page: int
    chunk_index: int
    text: str


class Evidence(BaseModel):
    id: str
    document_id: str
    organization_id: str | None = None
    version: str
    title: str
    page: int | None = None
    chunk_index: int = 0
    snippet: str
    score: float


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    equipment_model: str = Field(
        min_length=1, max_length=MAX_EQUIPMENT_MODEL_LENGTH
    )
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    version: str = Field(default="1.0", max_length=MAX_VERSION_LENGTH)
    source: str = Field(default="", max_length=MAX_SOURCE_LENGTH)

    @field_validator("title", "equipment_model", "content", "version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("不能为空白字符")
        return value


class IngestResponse(BaseModel):
    document_id: str
    title: str
    page_count: int
    chunk_count: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    equipment_model: str | None = Field(
        default=None, max_length=MAX_EQUIPMENT_MODEL_LENGTH
    )
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("不能为空白字符")
        return value


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[Evidence]
