from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Any

from src.api.schemas.request import AnalyzeRequest
from src.api.schemas.response import HistoryResponse
from src.api.dependencies import get_patent_agent, get_history_manager
from src.api.services.analyze_service import process_analysis_stream
from src.patent_agent import PatentAgent
from src.history_manager import HistoryManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", summary="특허 분석 요청 (SSE 스트리밍 연동)")
async def analyze_patent(
    request: AnalyzeRequest,
    req: Request,
    agent: PatentAgent = Depends(get_patent_agent),
    history: HistoryManager = Depends(get_history_manager)
):
    try:
        # Check if streaming is requested
        if request.stream:
            # We use text/event-stream for SSE
            return StreamingResponse(
                process_analysis_stream(request, agent, history),
                media_type="text/event-stream"
            )
        else:
            # Full blocking wait
            result = await agent.analyze(
                user_idea=request.user_idea,
                use_hybrid=request.use_hybrid,
                stream=False
            )
            # Save history
            history.save_analysis(result, user_id=request.user_id)
            return result
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", summary="과거 검색 기록 조회", response_model=HistoryResponse)
async def get_history(
    user_id: str = Query(..., description="사용자 식별자"),
    limit: int = Query(20, description="최대 조회 개수"),
    history: HistoryManager = Depends(get_history_manager)
):
    try:
        history_items = history.load_recent(user_id=user_id, limit=limit)
        return HistoryResponse(user_id=user_id, history=history_items)
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")
