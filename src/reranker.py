"""
Reranker Module - Cross-Encoder 기반 검색 결과 재정렬 모듈.

Cross-Encoder 모델(sentence-transformers)을 사용하여 초기 검색 결과를
쿼리-문서 쌍의 관련성 점수로 재정렬합니다.

특징:
- GPU/CPU 자동 감지 (torch.cuda.is_available())
- sentence-transformers 미설치 시 graceful degradation
- asyncio 호환: 동기 블로킹 연산은 asyncio.to_thread()로 호출 권장
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 기본 모델명 — 경량 Cross-Encoder (성능/속도 균형)
_DEFAULT_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """Cross-Encoder 기반 문서 재정렬기.

    sentence-transformers 라이브러리의 CrossEncoder를 래핑하여
    쿼리와 문서 쌍의 관련성을 점수화합니다.

    Args:
        model_name: HuggingFace 모델 식별자. 기본값은 ms-marco MiniLM-L-6.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL_NAME) -> None:
        self.model_name: str = model_name
        # CrossEncoder 인스턴스; 로드 실패 시 None 유지
        self.model: Optional[Any] = None
        self._load_model()

    def _load_model(self) -> None:
        """CrossEncoder 모델을 적절한 디바이스로 로드합니다.

        sentence-transformers 미설치 또는 모델 로드 실패 시
        경고 로그를 기록하고 조용히 실패합니다 (self.model = None).
        """
        try:
            import torch
            from sentence_transformers import CrossEncoder  # type: ignore[import]

            # GPU 가용 여부에 따라 디바이스 자동 선택
            device: str = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(
                "Reranker 모델 로딩 중",
                extra={"model": self.model_name, "device": device},
            )
            self.model = CrossEncoder(self.model_name, device=device)
            logger.info("Reranker 모델 로드 완료", extra={"model": self.model_name})

        except ImportError:
            logger.warning(
                "sentence-transformers가 설치되지 않아 Reranker가 비활성화됩니다. "
                "`pip install sentence-transformers`로 설치하세요."
            )
        except Exception:
            logger.exception(
                "Reranker 모델 로드 실패",
                extra={"model": self.model_name},
            )

    @property
    def is_available(self) -> bool:
        """Reranker 모델이 정상 로드되었는지 여부를 반환합니다."""
        return self.model is not None

    def rerank(
        self,
        query: str,
        docs: List[Dict[str, Any]],
        top_k: int = 5,
        text_max_length: int = 1000,
    ) -> List[Dict[str, Any]]:
        """쿼리와 문서 목록을 Cross-Encoder로 재정렬합니다.

        Args:
            query: 사용자 검색 쿼리.
            docs: 재정렬 대상 문서 딕셔너리 목록.
                  각 딕셔너리에 'title', 'abstract' 키가 있으면 활용됩니다.
            top_k: 반환할 상위 문서 수.
            text_max_length: 모델 입력 텍스트 최대 길이 (문자 기준).

        Returns:
            'rerank_score' 키가 추가된 문서 목록 (관련성 내림차순 정렬).
            모델이 비활성 상태이거나 오류 발생 시 원본 목록의 상위 top_k를 반환합니다.
        """
        # 모델 미로드 또는 빈 입력 → 폴백
        if not self.is_available or not docs:
            return docs[:top_k]

        # (query, document_text) 쌍 생성
        pairs: List[List[str]] = [
            [
                query,
                f"{doc.get('title', '')} {doc.get('abstract', '')} {doc.get('claims', '')}"[:text_max_length],
            ]
            for doc in docs
        ]

        try:
            scores = self.model.predict(pairs)

            # 각 문서에 rerank_score 부여
            for doc, score in zip(docs, scores):
                doc["rerank_score"] = float(score)

            # 점수 내림차순 정렬 후 top_k 반환
            docs.sort(key=lambda d: d.get("rerank_score", 0.0), reverse=True)
            logger.info(
                "Reranking 완료",
                extra={"docs_reranked": len(docs), "top_k": top_k},
            )
            return docs[:top_k]

        except Exception:
            logger.exception("Reranking 중 오류 발생. 원본 순서로 반환합니다.")
            return docs[:top_k]
