from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    alerts,
    audit_events,
    devices,
    diagnoses,
    maintenance_records,
    work_orders,
)
from app.api.errors import ERROR_CODES
from app.schemas.chat import ChatRequest, ChatResponse


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


DOCS_ENABLED = os.getenv("DOCS_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
}
WRITE_API_KEY = os.getenv("WRITE_API_KEY", "")

app = FastAPI(
    title="制造领航 ForgePilot API",
    description="面向中小制造企业的设备知识、故障诊断与维护协同 API。",
    version="0.1.0",
    default_response_class=UTF8JSONResponse,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

default_origins = "http://localhost:5173,http://127.0.0.1:5173"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", default_origins).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def write_protection(request: Request, call_next):
    if (
        WRITE_API_KEY
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path.startswith("/api/v1/")
    ):
        provided = request.headers.get("X-Write-Key", "")
        if not hmac.compare_digest(provided, WRITE_API_KEY):
            return UTF8JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "缺少或无效的写入凭证",
                    }
                },
            )
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        content = detail
    else:
        content = {
            "error": {
                "code": ERROR_CODES.get(exc.status_code, "ERROR"),
                "message": str(detail),
            }
        }
    return UTF8JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return UTF8JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数不合法",
                "details": {"errors": jsonable_encoder(exc.errors())},
            }
        },
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return ChatResponse(
        device_id=request.device_id,
        answer="这是第 1 周的模拟诊断回答。",
        sources=[],
        is_mock=True,
    )


app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(work_orders.router)
app.include_router(diagnoses.router)
app.include_router(audit_events.router)
app.include_router(maintenance_records.router)
