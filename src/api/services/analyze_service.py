import json
import logging
from typing import AsyncGenerator
from src.patent_agent import PatentAgent
from src.history_manager import HistoryManager
from src.api.schemas.request import AnalyzeRequest
from src.api.schemas.response import AnalyzeResponse
from src.security import PromptInjectionError, sanitize_user_input

logger = logging.getLogger(__name__)

async def process_analysis_stream(
    request: AnalyzeRequest,
    agent: PatentAgent,
    history: HistoryManager
) -> AsyncGenerator[str, None]:
    """
    Process analysis and stream results using SSE format.
    """
    try:
        # 1. Start pipeline: Send initial setup/metadata
        yield f"data: {json.dumps({'status': 'processing', 'message': 'Starting analysis...'})}\n\n"
        
        # Security sanitization happens inside agent.analyze but let's do initial check
        try:
            sanitized_idea = sanitize_user_input(request.user_idea)
        except PromptInjectionError as e:
            logger.error(f"[Security] Analysis blocked: {e}")
            yield f"data: {json.dumps({'error': str(e), 'security_alert': True})}\n\n"
            return

        # 2. Search & initial grading
        yield f"data: {json.dumps({'status': 'searching', 'message': 'Searching and grading patents...'})}\n\n"
        results = await agent.search_with_grading(sanitized_idea, use_hybrid=request.use_hybrid)
        
        if not results:
            yield f"data: {json.dumps({'error': 'No relevant patents found'})}\n\n"
            return
            
        # Send search results
        search_results_data = [
            {
                "patent_id": r.publication_number,
                "title": r.title,
                "abstract": r.abstract,
                "claims": r.claims,
                "grading_score": r.grading_score,
                "grading_reason": r.grading_reason,
                "dense_score": r.dense_score,
                "sparse_score": r.sparse_score,
                "rrf_score": r.rrf_score,
            }
            for r in results
        ]
        
        yield f"data: {json.dumps({'status': 'search_complete', 'results': search_results_data})}\n\n"
        
        # 3. Stream Critical Analysis
        yield f"data: {json.dumps({'status': 'analyzing', 'message': 'Streaming critical analysis...'})}\n\n"
        
        async for chunk in agent.critical_analysis_stream(sanitized_idea, results):
            # Send chunks to client. Encode to handle newlines properly
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
        # 4. Save to history (Not fully structured through stream so we just save basic info)
        # Ideally, we reconstruct the streamed output, or modify PatentAgent to do it.
        # As stream is plain markdown, we just notify completion.
        yield f"data: {json.dumps({'status': 'complete', 'message': 'Analysis finished'})}\n\n"
        
    except Exception as e:
        logger.error(f"Analysis streaming failed: {e}")
        yield f"data: {json.dumps({'error': 'Internal Server Error' })}\n\n"
