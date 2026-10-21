from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.store import KnowledgeBase
from app.deps import get_kb, get_rag
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.document import (
    Document,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.rag import RAGService

router = APIRouter(prefix="/api/v1", tags=["rag"])


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, kb: KnowledgeBase = Depends(get_kb)):
    results = kb.search(
        request.query,
        equipment_model=request.equipment_model,
        top_k=request.top_k,
    )
    return SearchResponse(query=request.query, count=len(results), results=results)


@router.post("/documents/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, kb: KnowledgeBase = Depends(get_kb)):
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


@router.get("/documents", response_model=list[Document])
def list_documents(kb: KnowledgeBase = Depends(get_kb)):
    return kb.list_documents()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, rag: RAGService = Depends(get_rag)):
    return rag.diagnose(
        device_id=request.device_id,
        question=request.question,
        equipment_model=request.equipment_model,
    )
