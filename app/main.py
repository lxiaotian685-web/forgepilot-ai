from fastapi import FastAPI

from app.schemas.chat import ChatRequest, ChatResponse

app = FastAPI(
    title="制造领航 ForgePilot API",
    description="面向中小制造企业的设备知识、故障诊断与维护协同 API。",
    version="0.1.0",
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
