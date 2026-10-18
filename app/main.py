from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import STORAGE_PATH
from app.core.store import KnowledgeBase
from app.llm.mock import MockLLM
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.document import (
    Document,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.rag import RAGService

kb = KnowledgeBase(STORAGE_PATH)
rag = RAGService(kb, MockLLM())


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb.load()
    yield


app = FastAPI(
    title="制造领航 ForgePilot API",
    description="面向中小制造企业的设备知识、故障诊断与维护协同 API。",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/v1/search", response_model=SearchResponse)
def search(request: SearchRequest):
    results = kb.search(
        request.query,
        equipment_model=request.equipment_model,
        top_k=request.top_k,
    )
    return SearchResponse(query=request.query, count=len(results), results=results)


@app.post("/api/v1/documents/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    document, chunks = kb.ingest(
        title=request.title,
        equipment_model=request.equipment_model,
        content=request.content,
        version=request.version,
        source=request.source,
    )
    return IngestResponse(
        document_id=document.id,
        title=document.title,
        page_count=document.page_count,
        chunk_count=len(chunks),
    )


@app.get("/api/v1/documents", response_model=list[Document])
def list_documents():
    return kb.list_documents()


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return rag.diagnose(
        device_id=request.device_id,
        question=request.question,
        equipment_model=request.equipment_model,
    )
