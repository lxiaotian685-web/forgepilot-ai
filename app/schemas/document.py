from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    title: str
    equipment_model: str
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
    version: str
    title: str
    page: int | None = None
    chunk_index: int = 0
    snippet: str
    score: float


class IngestRequest(BaseModel):
    title: str = Field(min_length=1)
    equipment_model: str = Field(min_length=1)
    content: str = Field(min_length=1)
    version: str = "1.0"
    source: str = ""


class IngestResponse(BaseModel):
    document_id: str
    title: str
    page_count: int
    chunk_count: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    equipment_model: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[Evidence]
