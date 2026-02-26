"""
Patent Guard v2.0 - FastAPI Backend API
=======================================
Stateless REST API and Streaming SSE endpoint for Patent Analysis.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from src.vector_db import PineconeClient
from src.history_manager import HistoryManager
from src.analysis_logic import run_full_analysis
from src.rate_limiter import RateLimitException, check_rate_limit

logger = logging.getLogger(__name__)

# CORS 허용 Origin을 환경 변수로 관리 (보안 강화)
# 운영 환경에서는 쉼표로 구분된 도메인 목록을 주입하세요.
# 예: ALLOWED_ORIGINS="https://app.short-cut.io,https://admin.short-cut.io"
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ─── 앱 수명 주기 관리 (FastAPI 0.93+ 권장 방식) ─────────────────────────────
# @app.on_event("startup") deprecated → lifespan context manager 사용
db_client: Optional[PineconeClient] = None
history_manager: Optional[HistoryManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 리소스를 초기화하고 정리합니다."""
    global db_client, history_manager

    # — 시작 로직 —
    try:
        db_client = PineconeClient(skip_init_check=True)
        logger.info("Pinecone DB client initialized.")
    except Exception as e:
        logger.error(f"Failed to load Pinecone DB: {e}")

    try:
        history_manager = HistoryManager()
        logger.info("HistoryManager initialized.")
    except Exception as e:
        logger.error(f"Failed to load HistoryManager: {e}")

    yield  # 앱 실행 구간

    # — 종료 로직 (필요 시 커넥션 정리) —
    logger.info("Application shutdown. Cleaning up resources.")


app = FastAPI(
    title="Short-Cut Patent API",
    description="Stateless Backend API for Patent Guard v2.0",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 - 명시적 도메인만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitException)
async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "message": exc.message,
            "reset_time": exc.reset_time
        }
    )


class AnalyzeRequest(BaseModel):
    user_idea: str
    user_id: str
    use_hybrid: bool = True
    # Pydantic v2 호환 Optional 타입 선언
    ipc_filters: Optional[List[str]] = None


@app.post("/api/v1/analyze", dependencies=[Depends(check_rate_limit)])
async def analyze_idea_stream(req: AnalyzeRequest):
    """
    Stream patent analysis process to client using Server-Sent Events (SSE).
    """
    if not db_client:
        raise HTTPException(status_code=503, detail="Database client is unavailable.")

    async def event_generator():
        try:
            async for event in run_full_analysis(
                user_idea=req.user_idea,
                user_id=req.user_id,
                db_client=db_client,
                history_manager=history_manager,
                use_hybrid=req.use_hybrid,
                ipc_filters=req.ipc_filters
            ):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            logger.error(f"Analysis stream error: {e}")
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/history/{user_id}")
async def get_history(user_id: str):
    """Get analysis history for a specific user."""
    if not history_manager:
        raise HTTPException(status_code=503, detail="History manager unavailable.")

    try:
        history = history_manager.load_recent(user_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
