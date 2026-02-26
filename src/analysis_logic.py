"""
핵심 분석 로직 오케스트레이션 모듈 (Stateless API 버전).

RAG 파이프라인의 전체 흐름을 조율합니다:
    1. 캐시 확인 (HistoryManager)
    2. HyDE + Multi-Query 검색
    3. Cross-Encoder 재정렬 (Reranker)
    4. LLM 관련성 평가 (Grading)
    5. 스트리밍 분석 (Streaming CoT Analysis)
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.patent_agent import PatentAgent, PatentSearchResult

logger = logging.getLogger(__name__)

# =============================================================================
# Reranker 싱글턴 캐시 (모듈 수준 지연 초기화)
# =============================================================================

# Reranker는 모델 가중치 로딩 비용이 크므로 전역 싱글턴으로 관리
_reranker_instance: Optional[Any] = None


def get_reranker() -> Optional[Any]:
    """Reranker 모델을 지연 로드하여 싱글턴으로 반환합니다.

    최초 호출 시 모델을 로드하고, 이후 호출에서는 캐시된 인스턴스를 반환합니다.
    로드에 실패하면 None을 반환하며 재시도하지 않습니다 (False 센티넬 패턴).

    Returns:
        초기화된 Reranker 인스턴스 또는 None (로드 실패 시).
    """
    global _reranker_instance  # noqa: PLW0603

    if _reranker_instance is None:
        try:
            from src.reranker import Reranker  # 순환 임포트 방지용 지연 임포트

            instance = Reranker()
            # is_available 프로퍼티로 모델 로드 성공 여부 확인
            _reranker_instance = instance if instance.is_available else False  # type: ignore[assignment]
        except Exception:
            logger.exception("Reranker 로드 실패. Reranker 없이 계속 진행합니다.")
            _reranker_instance = False  # type: ignore[assignment]

    # False(실패 센티넬)인 경우 None 반환
    return _reranker_instance if _reranker_instance else None  # type: ignore[return-value]


# =============================================================================
# 내부 헬퍼: 스트리밍 분석 실행
# =============================================================================


async def _run_analysis_streaming(
    agent: PatentAgent,
    user_idea: str,
    results: List[PatentSearchResult],
) -> AsyncGenerator[Dict[str, Any], None]:
    """스트리밍 분석을 실행하고 토큰/전체 텍스트 이벤트를 yield합니다.

    Args:
        agent: 초기화된 PatentAgent 인스턴스.
        user_idea: 사용자 아이디어 텍스트.
        results: 검색 및 재정렬된 특허 결과 목록.

    Yields:
        {"type": "stream_token", "content": str} — 각 스트리밍 토큰.
        {"type": "stream_full", "content": str} — 완전한 스트리밍 텍스트.
    """
    full_text: str = ""
    async for token in agent.critical_analysis_stream(user_idea, results):
        full_text += token
        yield {"type": "stream_token", "content": token}

    yield {"type": "stream_full", "content": full_text}


# =============================================================================
# 공개 API: 전체 분석 파이프라인
# =============================================================================


async def run_full_analysis(
    user_idea: str,
    user_id: str,
    db_client: Any,
    history_manager: Optional[Any] = None,
    use_hybrid: bool = True,
    ipc_filters: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """완전한 특허 분석 파이프라인을 스트리밍 방식으로 실행합니다.

    진행 상태, 스트리밍 토큰, 최종 결과를 딕셔너리 이벤트로 yield합니다.

    Args:
        user_idea: 사용자가 입력한 아이디어 텍스트.
        user_id: 분석 결과 캐싱을 위한 사용자 식별자.
        db_client: 초기화된 벡터 DB 클라이언트 (PineconeClient 등).
        history_manager: 결과 캐싱을 위한 HistoryManager 인스턴스 (선택).
        use_hybrid: True면 Dense+Sparse 하이브리드 검색 사용.
        ipc_filters: IPC 코드 접두어 필터 목록 (예: ['G06', 'H04']).

    Yields:
        다양한 type의 딕셔너리 이벤트:
        - "info": 상태 메시지
        - "progress": 진행률 및 메시지
        - "step_info": 단계별 상세 정보
        - "queries": 생성된 검색 쿼리 목록
        - "stream_token": LLM 스트리밍 토큰
        - "result": 최종 분석 결과 딕셔너리
    """
    # ------------------------------------------------------------------
    # 0. 캐시 확인
    # ------------------------------------------------------------------
    if history_manager and not ipc_filters:
        cached_result = history_manager.find_cached_result(user_idea, user_id)
        if cached_result:
            yield {"type": "info", "message": "⚡ 이미 분석된 아이디어입니다. 저장된 결과를 불러옵니다."}
            await asyncio.sleep(0.5)
            yield {"type": "result", "data": cached_result}
            return

    # ------------------------------------------------------------------
    # 1. 에이전트 및 Reranker 초기화
    # ------------------------------------------------------------------
    agent = PatentAgent(db_client=db_client)
    reranker = get_reranker()

    results: List[PatentSearchResult] = []
    start_time: float = time.monotonic()  # perf counter 사용 (절대 시간 불필요)

    yield {"type": "progress", "percent": 0, "message": "🚀 분석 시작..."}

    # ------------------------------------------------------------------
    # 2. Step 1: HyDE 가상 청구항 생성 (~3초)
    # ------------------------------------------------------------------
    yield {
        "type": "progress",
        "percent": 5,
        "message": "📝 Step 1/5: 가상 청구항 생성 중... (예상: 3초)",
    }
    yield {"type": "step_info", "step": 1, "message": "HyDE - 가상 청구항 생성 중..."}

    await agent.generate_hypothetical_claim(user_idea)

    yield {"type": "progress", "percent": 20, "message": "✅ Step 1 완료!"}

    # ------------------------------------------------------------------
    # 3. Step 2: Multi-Query 하이브리드 검색 (~4초)
    # ------------------------------------------------------------------
    search_type = "Multi-Query Hybrid" if use_hybrid else "Multi-Query Dense"
    if ipc_filters:
        search_type += f" (IPC 필터: {', '.join(ipc_filters)})"

    yield {
        "type": "progress",
        "percent": 25,
        "message": f"🔎 Step 2/5: {search_type} 검색 중... (예상: 4초)",
    }
    yield {
        "type": "step_info",
        "step": 2,
        "message": f"{search_type} 검색 중... (3가지 관점)",
    }

    # Top-15 후보 검색
    queries, search_results = await agent.search_multi_query(
        user_idea,
        top_k=15,
        use_hybrid=use_hybrid,
        ipc_filters=ipc_filters,
    )

    yield {"type": "queries", "data": queries}
    yield {"type": "progress", "percent": 45, "message": "✅ Step 2 완료!"}
    yield {
        "type": "info",
        "message": f"✅ {len(search_results)}개 후보 특허 발견 (중복 제거됨)",
    }

    # ------------------------------------------------------------------
    # 4. Step 3: Cross-Encoder 재정렬 (~3초)
    # ------------------------------------------------------------------
    if reranker and search_results:
        yield {
            "type": "progress",
            "percent": 50,
            "message": "🎯 Step 3/5: Cross-Encoder 정밀 재정렬 중... (예상: 3초)",
        }
        yield {
            "type": "step_info",
            "step": 3,
            "message": "Cross-Encoder 정밀 재정렬 중...",
        }

        # reranker.rerank()는 CPU 블로킹 동기 연산이므로
        # asyncio.to_thread()로 스레드풀에서 실행하여 이벤트 루프를 보호
        docs_for_rerank: List[Dict[str, Any]] = [
            {
                "doc_obj": r,  # 원본 객체 참조 보존
                "title": r.title,
                "abstract": r.abstract,
                "claims": r.claims,
            }
            for r in search_results
        ]
        reranked_docs = await asyncio.to_thread(
            reranker.rerank, user_idea, docs_for_rerank, top_k=5
        )

        results = [doc["doc_obj"] for doc in reranked_docs]
        yield {"type": "info", "message": "✅ Top 5 특허 선정 완료 (Reranked)"}
    else:
        results = search_results[:5]
        yield {"type": "info", "message": "⚠️ Reranker 미사용 (Top 5 반환)"}

    yield {"type": "progress", "percent": 60, "message": "✅ Step 3 완료!"}

    # ------------------------------------------------------------------
    # 5. Step 4: LLM 관련성 평가 (~3초)
    # ------------------------------------------------------------------
    yield {
        "type": "progress",
        "percent": 65,
        "message": "📊 Step 4/5: 관련성 평가 중... (예상: 3초)",
    }
    yield {"type": "step_info", "step": 4, "message": "LLM 관련성 평가 중..."}

    grading = await agent.grade_results(user_idea, results)

    yield {"type": "progress", "percent": 80, "message": "✅ Step 4 완료!"}
    yield {
        "type": "info",
        "message": f"✅ 평균 관련성 점수: {grading.average_score:.2f}",
    }

    # ------------------------------------------------------------------
    # 6. Step 5: AI 스트리밍 분석 (~10초)
    # ------------------------------------------------------------------
    yield {
        "type": "progress",
        "percent": 85,
        "message": "🧠 Step 5/5: AI 분석 스트리밍 중... (예상: 10초)",
    }
    yield {
        "type": "step_info",
        "step": 5,
        "message": "AI가 분석 내용을 실시간으로 생성합니다...",
    }

    streamed_text: str = ""
    async for stream_event in _run_analysis_streaming(agent, user_idea, results):
        if stream_event["type"] == "stream_token":
            yield {"type": "stream_token", "content": stream_event["content"]}
        elif stream_event["type"] == "stream_full":
            streamed_text = stream_event["content"]

    # 스트리밍 결과를 경량 모델(GPT-4o-mini)으로 JSON 구조화 파싱 (비용 절감)
    # 기존: GPT-4o 2차 호출 → 최적화: GPT-4o-mini 파싱 (~50% 비용 절감)
    analysis = await agent.parse_streaming_to_structured(user_idea, streamed_text, results)

    # ------------------------------------------------------------------
    # 7. 최종 결과 조합 및 yield
    # ------------------------------------------------------------------
    elapsed: float = time.monotonic() - start_time
    yield {
        "type": "progress",
        "percent": 100,
        "message": f"✅ 분석 완료! (소요 시간: {elapsed:.1f}초)",
    }

    final_result: Dict[str, Any] = {
        "user_idea": user_idea,
        "search_results": [
            {
                "patent_id": getattr(r, "publication_number", str(getattr(r, "id", ""))),
                "title": r.title,
                "abstract": r.abstract,
                "claims": r.claims,
                "grading_score": getattr(r, "grading_score", 0.0),
                "grading_reason": getattr(r, "grading_reason", ""),
                "rrf_score": getattr(r, "rrf_score", 0.0),
            }
            for r in results
        ],
        "analysis": {
            "similarity": {
                "score": getattr(analysis.similarity, "score", 0),
                "common_elements": getattr(analysis.similarity, "common_elements", []),
                "summary": getattr(analysis.similarity, "summary", ""),
                "evidence": getattr(analysis.similarity, "evidence_patents", []),
            },
            "infringement": {
                "risk_level": getattr(analysis.infringement, "risk_level", "unknown"),
                "risk_factors": getattr(analysis.infringement, "risk_factors", []),
                "summary": getattr(analysis.infringement, "summary", ""),
                "evidence": getattr(analysis.infringement, "evidence_patents", []),
            },
            "avoidance": {
                "strategies": getattr(analysis.avoidance, "strategies", []),
                "alternatives": getattr(analysis.avoidance, "alternative_technologies", []),
                "summary": getattr(analysis.avoidance, "summary", ""),
                "evidence": getattr(analysis.avoidance, "evidence_patents", []),
            },
            "component_comparison": {
                "idea_components": getattr(
                    analysis.component_comparison, "idea_components", []
                ),
                "matched_components": getattr(
                    analysis.component_comparison, "matched_components", []
                ),
                "unmatched_components": getattr(
                    analysis.component_comparison, "unmatched_components", []
                ),
                "risk_components": getattr(
                    analysis.component_comparison, "risk_components", []
                ),
            },
            "conclusion": getattr(analysis, "conclusion", ""),
        },
        "streamed_analysis": streamed_text,
        "timestamp": datetime.now().isoformat(),
        "search_type": "hybrid" if use_hybrid else "dense",
    }

    yield {"type": "result", "data": final_result}
