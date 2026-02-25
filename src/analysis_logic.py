"""
Core analysis logic orchestration (Stateless API version).
"""
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from src.patent_agent import PatentAgent
from src.history_manager import HistoryManager

# Global singleton cache for reranker (to replace @st.cache_resource)
_RERANKER_INSTANCE = None

def get_reranker():
    """Load Reranker model (cached)."""
    global _RERANKER_INSTANCE
    if _RERANKER_INSTANCE is None:
        try:
            from src.reranker import Reranker
            _RERANKER_INSTANCE = Reranker()
        except Exception as e:
            print(f"Reranker load failed: {e}")
            _RERANKER_INSTANCE = False # Failed, don't try again
    return _RERANKER_INSTANCE if _RERANKER_INSTANCE else None


async def run_analysis_streaming(agent, user_idea: str, results) -> AsyncGenerator[Dict[str, Any], None]:
    """Run streaming analysis and yield tokens."""
    full_text = ""
    async for token in agent.critical_analysis_stream(user_idea, results):
        full_text += token
        yield {"type": "stream_token", "content": token}
    
    yield {"type": "stream_full", "content": full_text}


async def run_full_analysis(
    user_idea: str, 
    user_id: str,
    db_client, 
    history_manager: Optional[HistoryManager] = None,
    use_hybrid: bool = True,
    ipc_filters: list = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run the complete patent analysis with streaming.
    Yields dictionary events such as progress updates, stream tokens, and the final result.
    """
    
    # Check for cached result first
    if history_manager and not ipc_filters:
        cached_result = history_manager.find_cached_result(user_idea, user_id)
        if cached_result:
            yield {"type": "info", "message": "⚡ 이미 분석된 아이디어입니다. 저장된 결과를 불러옵니다."}
            await asyncio.sleep(0.5)
            yield {"type": "result", "data": cached_result}
            return

    # Create agent with cached DB client
    agent = PatentAgent(db_client=db_client)
    
    # Load Reranker
    reranker = get_reranker()
    
    results = []
    start_time = time.time()
    
    # Progress bar init
    yield {"type": "progress", "percent": 0, "message": "🚀 분석 시작..."}
    
    # Step 1: HyDE (~3초)
    yield {"type": "progress", "percent": 5, "message": "📝 Step 1/5: 가상 청구항 생성 중... (예상: 3초)"}
    yield {"type": "step_info", "step": 1, "message": "HyDE - 가상 청구항 생성 중..."}
    hypothetical_claim = await agent.generate_hypothetical_claim(user_idea)
    yield {"type": "progress", "percent": 20, "message": "✅ Step 1 완료!"}
    
    # Step 2: Multi-Query Search (~4초)
    search_type = "Multi-Query Hybrid" if use_hybrid else "Multi-Query Dense"
    if ipc_filters:
        search_type += f" (IPC 필터: {', '.join(ipc_filters)})"
        
    yield {"type": "progress", "percent": 25, "message": f"🔎 Step 2/5: {search_type} 검색 중... (예상: 4초)"}
    yield {"type": "step_info", "step": 2, "message": f"{search_type} 검색 중... (3가지 관점)"}
    
    # Use Multi-Query Search (Parallel) -> Get Top 15 candidates
    queries, search_results = await agent.search_multi_query(
        user_idea, top_k=15, use_hybrid=use_hybrid, ipc_filters=ipc_filters
    )
    
    # Emit generated queries
    yield {"type": "queries", "data": queries}
    
    yield {"type": "progress", "percent": 45, "message": "✅ Step 2 완료!"}
    yield {"type": "info", "message": f"✅ {len(search_results)}개 후보 특허 발견 (중복 제거됨)"}
    
    # Step 3: Reranking (~3초)
    if reranker and search_results:
        yield {"type": "progress", "percent": 50, "message": "🎯 Step 3/5: Cross-Encoder 정밀 재정렬 중... (예상: 3초)"}
        yield {"type": "step_info", "step": 3, "message": "Cross-Encoder 정밀 재정렬 중..."}
        
        # Convert PatentSearchResult to dict for Reranker
        docs_for_rerank = []
        for r in search_results:
            docs_for_rerank.append({
                "doc_obj": r, # Keep original object reference
                "title": r.title,
                "abstract": r.abstract,
                "claims": r.claims
            })
        
        # reranker.rerank()는 CPU 블로킹 동기 연산이므로
        # asyncio.to_thread()로 스레드풀에서 실행하여 이벤트 루프를 보호합니다.
        reranked_docs = await asyncio.to_thread(
            reranker.rerank, user_idea, docs_for_rerank, top_k=5
        )
        
        # Update results list
        results = []
        for doc in reranked_docs:
            r = doc['doc_obj']
            results.append(r)
            
        yield {"type": "info", "message": f"✅ Top 5 특허 선정 완료 (Reranked)"}
    else:
        results = search_results[:5]
        yield {"type": "info", "message": "⚠️ Reranker 미사용 (Top 5 반환)"}
        
    yield {"type": "progress", "percent": 60, "message": "✅ Step 3 완료!"}
    
    # Step 4: Grading (~3초)
    yield {"type": "progress", "percent": 65, "message": "📊 Step 4/5: 관련성 평가 중... (예상: 3초)"}
    yield {"type": "step_info", "step": 4, "message": "LLM 관련성 평가 중..."}
    grading = await agent.grade_results(user_idea, results)
    yield {"type": "progress", "percent": 80, "message": "✅ Step 4 완료!"}
    yield {"type": "info", "message": f"✅ 평균 관련성 점수: {grading.average_score:.2f}"}
    
    # Step 5: Streaming Analysis (~10초)
    yield {"type": "progress", "percent": 85, "message": "🧠 Step 5/5: AI 분석 스트리밍 중... (예상: 10초)"}
    yield {"type": "step_info", "step": 5, "message": "AI가 분석 내용을 실시간으로 생성합니다..."}
    
    streamed_text = ""
    async for stream_event in run_analysis_streaming(agent, user_idea, results):
        if stream_event["type"] == "stream_token":
            yield {"type": "stream_token", "content": stream_event["content"]}
        elif stream_event["type"] == "stream_full":
            streamed_text = stream_event["content"]
    
    # Also get structured analysis for result storage
    analysis = await agent.critical_analysis(user_idea, results)
    
    # Complete progress bar
    elapsed = time.time() - start_time
    yield {"type": "progress", "percent": 100, "message": f"✅ 분석 완료! (소요 시간: {elapsed:.1f}초)"}
    
    # Build final result payload
    final_result = {
        "user_idea": user_idea,
        "search_results": [
            {
                "patent_id": getattr(r, 'publication_number', str(getattr(r, 'id', ''))),
                "title": r.title,
                "abstract": r.abstract,
                "claims": r.claims,
                "grading_score": getattr(r, 'grading_score', 0),
                "grading_reason": getattr(r, 'grading_reason', ""),
                "rrf_score": getattr(r, 'rrf_score', 0),
            }
            for r in results
        ],
        "analysis": {
            "similarity": {
                "score": getattr(analysis.similarity, 'score', 0),
                "common_elements": getattr(analysis.similarity, 'common_elements', []),
                "summary": getattr(analysis.similarity, 'summary', ""),
                "evidence": getattr(analysis.similarity, 'evidence_patents', []),
            },
            "infringement": {
                "risk_level": getattr(analysis.infringement, 'risk_level', "Unknown"),
                "risk_factors": getattr(analysis.infringement, 'risk_factors', []),
                "summary": getattr(analysis.infringement, 'summary', ""),
                "evidence": getattr(analysis.infringement, 'evidence_patents', []),
            },
            "avoidance": {
                "strategies": getattr(analysis.avoidance, 'strategies', []),
                "alternatives": getattr(analysis.avoidance, 'alternative_technologies', []),
                "summary": getattr(analysis.avoidance, 'summary', ""),
                "evidence": getattr(analysis.avoidance, 'evidence_patents', []),
            },
            "component_comparison": {
                "idea_components": getattr(analysis.component_comparison, 'idea_components', []),
                "matched_components": getattr(analysis.component_comparison, 'matched_components', []),
                "unmatched_components": getattr(analysis.component_comparison, 'unmatched_components', []),
                "risk_components": getattr(analysis.component_comparison, 'risk_components', []),
            },
            "conclusion": getattr(analysis, 'conclusion', ""),
        },
        "streamed_analysis": streamed_text,
        "timestamp": datetime.now().isoformat(),
        "search_type": "hybrid" if use_hybrid else "dense",
    }
    
    yield {"type": "result", "data": final_result}
