from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import JSONResponse

from app.api.context import RequestContext, get_request_context
from app.config import ingest_enabled, max_upload_bytes
from app.core.device_provider import DeviceAuth
from app.core.store import KnowledgeBase
from app.core.upload import UploadError, parse_document, safe_filename
from app.deps import get_kb, get_rag
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.document import (
    MAX_EQUIPMENT_MODEL_LENGTH,
    MAX_SOURCE_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_VERSION_LENGTH,
    Document,
    DocumentDetail,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.rag import RAGService

router = APIRouter(prefix="/api/v1", tags=["rag"])

_HTTP_STATUS = {
    "device_not_found": 404,
    "device_unauthorized": 403,
    "device_unavailable": 503,
    "device_mismatch": 502,
}


def _require_document_manager(context: RequestContext) -> None:
    if context.role is not None and context.role not in {"manager", "admin", "owner"}:
        raise HTTPException(status_code=403, detail="当前岗位无权管理知识文档")


@router.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    context: RequestContext = Depends(get_request_context),
    kb: KnowledgeBase = Depends(get_kb),
):
    results = kb.search(
        request.query,
        equipment_model=request.equipment_model,
        top_k=request.top_k,
        organization_id=context.organization_id,
    )
    return SearchResponse(query=request.query, count=len(results), results=results)


@router.post("/documents/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    context: RequestContext = Depends(get_request_context),
    kb: KnowledgeBase = Depends(get_kb),
):
    if not ingest_enabled():
        raise HTTPException(status_code=403, detail="文档入库接口已禁用")
    _require_document_manager(context)
    try:
        document, chunks = kb.ingest(
            title=request.title,
            equipment_model=request.equipment_model,
            organization_id=context.organization_id,
            content=request.content,
            version=request.version,
            source=request.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestResponse(
        document_id=document.id,
        title=document.title,
        equipment_model=document.equipment_model,
        version=document.version,
        source=document.source,
        page_count=document.page_count,
        chunk_count=len(chunks),
    )


def _form_text(
    value: str,
    field: str,
    max_length: int,
    *,
    default: str = "",
) -> str:
    text = (value or default).strip()
    if not text:
        raise HTTPException(status_code=422, detail=f"{field} 不能为空")
    if len(text) > max_length:
        raise HTTPException(status_code=422, detail=f"{field} 过长")
    return text


@router.post("/documents/upload", response_model=IngestResponse)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    equipment_model: str = Form(...),
    version: str = Form(default="1.0"),
    source: str = Form(default=""),
    context: RequestContext = Depends(get_request_context),
    kb: KnowledgeBase = Depends(get_kb),
):
    if not ingest_enabled():
        raise HTTPException(status_code=403, detail="文档入库接口已禁用")
    _require_document_manager(context)

    filename = safe_filename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=422, detail="缺少文件名")

    title_value = _form_text(
        title,
        "title",
        MAX_TITLE_LENGTH,
        default=Path(filename).stem or "未命名文档",
    )
    model_value = _form_text(
        equipment_model, "equipment_model", MAX_EQUIPMENT_MODEL_LENGTH
    )
    version_value = _form_text(
        version, "version", MAX_VERSION_LENGTH, default="1.0"
    )
    source_value = _form_text(
        source, "source", MAX_SOURCE_LENGTH, default=filename
    )

    limit = max_upload_bytes()
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="文件过大")
    if not data:
        raise HTTPException(status_code=422, detail="文件为空")

    try:
        pages = parse_document(filename, data)
    except UploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        document, chunks = kb.ingest_pages(
            title=title_value,
            equipment_model=model_value,
            pages=pages,
            organization_id=context.organization_id,
            version=version_value,
            source=source_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return IngestResponse(
        document_id=document.id,
        title=document.title,
        equipment_model=document.equipment_model,
        version=document.version,
        source=document.source,
        page_count=document.page_count,
        chunk_count=len(chunks),
    )


@router.get("/documents", response_model=list[Document])
def list_documents(
    context: RequestContext = Depends(get_request_context),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    kb: KnowledgeBase = Depends(get_kb),
):
    return kb.list_documents(
        organization_id=context.organization_id,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    context: RequestContext = Depends(get_request_context),
    kb: KnowledgeBase = Depends(get_kb),
):
    result = kb.get_document(document_id, context.organization_id)
    if result is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    document, chunks = result
    return DocumentDetail(
        document=document, chunks=chunks, chunk_count=len(chunks)
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    context: RequestContext = Depends(get_request_context),
    kb: KnowledgeBase = Depends(get_kb),
):
    _require_document_manager(context)
    if not kb.delete_document(document_id, context.organization_id):
        raise HTTPException(status_code=404, detail="文档不存在")


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    context: RequestContext = Depends(get_request_context),
    rag: RAGService = Depends(get_rag),
):
    result = rag.diagnose(
        device_id=payload.device_id,
        question=payload.question,
        equipment_model=payload.equipment_model,
        auth=DeviceAuth(
            token=context.token,
            organization_id=context.organization_id,
            user_id=context.user_id,
        ),
    )
    status_code = _HTTP_STATUS.get(result.status)
    if status_code is not None:
        return JSONResponse(
            status_code=status_code,
            content=result.model_dump(mode="json"),
        )
    return result
