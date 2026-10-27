from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.rag import router as rag_router
from app.config import env_bool, env_int
from app.core.demo import ensure_demo_documents
from app.deps import kb, rag
from app.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_demo_documents(kb)
    yield
    rag.llm.close()
    rag.device_provider.close()


docs_enabled = env_bool("DOCS_ENABLED", True)

app = FastAPI(
    title="制造领航 ForgePilot API",
    description="面向中小制造企业的设备知识、故障诊断与维护协同 API。",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
    max_bytes = env_int("MAX_REQUEST_BYTES", 6_000_000, minimum=1)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Content-Length 不合法"}
            )
        if length > max_bytes:
            return JSONResponse(
                status_code=413, content={"detail": "请求体过大"}
            )
    return await call_next(request)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    limit = env_int("RATE_LIMIT_PER_MINUTE", 60, minimum=0)
    if limit > 0 and request.url.path.startswith("/api/"):
        key = request.client.host if request.client else "unknown"
        if not limiter.allow(key, limit):
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": "60"},
            )
    return await call_next(request)


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(rag_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "device_provider": getattr(rag.device_provider, "source", "unknown"),
        "llm_provider": getattr(rag.llm, "name", type(rag.llm).__name__),
    }
