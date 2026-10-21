from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.rag import router as rag_router
from app.core.demo import ensure_demo_documents
from app.deps import kb, rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_demo_documents(kb)
    yield
    rag.llm.close()
    rag.device_provider.close()


app = FastAPI(
    title="制造领航 ForgePilot API",
    description="面向中小制造企业的设备知识、故障诊断与维护协同 API。",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(rag_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
