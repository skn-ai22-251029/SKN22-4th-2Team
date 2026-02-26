"""
쇼특허(Short-Cut) 공통 유틸리티 모듈.

책임:
1. 구조화 JSON 로깅 (JsonLineFormatter, configure_json_logging)
2. 로그 이벤트 식별자 상수 (LogEvent)
3. 분석 결과 포맷팅 헬퍼 (비-UI, 순수 함수)

주의: 이 모듈은 streamlit에 의존하지 않습니다.
      UI 전용 헬퍼는 src/ui_helpers.py 를 참조하세요.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple


# =============================================================================
# 구조화 JSON 로그 포맷터 (CloudWatch / ELK 연동용)
# =============================================================================


class JsonLineFormatter(logging.Formatter):
    """extra 필드를 포함한 JSON 라인 포맷터.

    표준 logging.Formatter는 extra 딕셔너리를 출력하지 않으므로,
    이 포맷터를 핸들러에 부착하면 모든 로그가 JSON 한 줄로 직렬화됩니다.
    CloudWatch Logs Insights, Kibana 등에서 직접 파싱 가능합니다.
    """

    # logging.LogRecord의 기본 속성 키 — extra 필드만 추출하기 위한 제외 목록
    _STANDARD_KEYS: frozenset = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    )

    def format(self, record: logging.LogRecord) -> str:
        """LogRecord를 JSON 문자열로 직렬화합니다."""
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # extra 필드 병합 (표준 키 제외)
        for key, value in record.__dict__.items():
            if key not in self._STANDARD_KEYS:
                log_obj[key] = value
        return json.dumps(log_obj, ensure_ascii=False, default=str)


def configure_json_logging(level: int = logging.INFO) -> None:
    """루트 로거에 JsonLineFormatter를 적용합니다.

    이미 핸들러가 존재하면 포맷터만 교체하고,
    없으면 StreamHandler를 추가합니다.

    Args:
        level: 로깅 레벨 (기본값: logging.INFO).
    """
    formatter = JsonLineFormatter()
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


# =============================================================================
# 로그 이벤트 키 상수 (오타 방지 및 검색 가용성 향상)
# =============================================================================


class LogEvent:
    """로그 이벤트 식별자 상수.

    로그 페이로드의 'event' 키에 사용하여 오타를 방지하고,
    CloudWatch Metric Filter 등에서 일관된 필터링을 보장합니다.
    """

    CUTOFF_FILTER: str = "cutoff_filter"
    HIGH_CUTOFF_WARNING: str = "high_cutoff_ratio_warning"
    ANALYSIS_CUTOFF: str = "analysis_cutoff_filter"


# =============================================================================
# 분석 결과 포맷팅 헬퍼 (순수 함수 — UI 의존 없음)
# =============================================================================


def get_risk_color(risk_level: str) -> Tuple[str, str, str]:
    """리스크 레벨에 따른 색상 스키마를 반환합니다.

    Args:
        risk_level: "high", "medium", "low" 중 하나.

    Returns:
        (hex_color, emoji, css_class) 튜플.
        알 수 없는 값은 gray/unknown 값으로 폴백됩니다.
    """
    # 리스크 레벨 → (hex 색상, 이모지, CSS 클래스) 매핑
    _RISK_COLOR_MAP: Dict[str, Tuple[str, str, str]] = {
        "high": ("#dc3545", "🔴", "metric-high"),
        "medium": ("#ffc107", "🟡", "metric-medium"),
        "low": ("#28a745", "🟢", "metric-low"),
    }
    return _RISK_COLOR_MAP.get(risk_level.lower(), ("#6c757d", "⚪", "metric-unknown"))


def get_score_color(score: int) -> str:
    """유사도 점수에 따른 hex 색상 코드를 반환합니다.

    Args:
        score: 0-100 범위의 유사도 점수.

    Returns:
        위험 수준에 맞는 hex 색상 코드 문자열.
    """
    if score >= 70:
        return "#dc3545"  # 위험 — 빨강
    if score >= 40:
        return "#ffc107"  # 주의 — 노랑
    return "#28a745"      # 안전 — 초록


def get_patent_link(patent_id: str) -> str:
    """특허 번호로부터 Google Patents URL을 생성합니다.

    Args:
        patent_id: 특허 공개 번호 (예: "KR-102842452-B1").

    Returns:
        Google Patents 링크 URL 문자열.
    """
    # URL에서 공백과 하이픈 제거
    clean_id = patent_id.replace(" ", "").replace("-", "")
    return f"https://patents.google.com/patent/{clean_id}"


def format_analysis_markdown(result: Dict[str, Any]) -> str:
    """분석 결과 딕셔너리를 다운로드 가능한 마크다운 문자열로 변환합니다.

    Args:
        result: run_full_analysis()가 yield하는 최종 결과 딕셔너리.

    Returns:
        마크다운 포맷의 보고서 문자열.
    """
    analysis = result.get("analysis", {})
    similarity = analysis.get("similarity", {})
    infringement = analysis.get("infringement", {})
    avoidance = analysis.get("avoidance", {})

    # 위험 요소 목록 마크다운 변환
    risk_factors_md: str = "\n".join(
        f"  - {f}" for f in infringement.get("risk_factors", [])
    )
    strategies_md: str = "\n".join(
        f"  - {s}" for s in avoidance.get("strategies", [])
    )

    md = f"""# ⚡ 쇼특허 (Short-Cut) Analysis Report
> Generated: {result.get('timestamp', datetime.now().isoformat())}
> Search Type: {result.get('search_type', 'hybrid').upper()}

## 💡 User Idea
{result.get('user_idea', 'N/A')}

---

## 📊 Analysis Summary

### [1. 유사도 평가] Similarity Assessment
- **Score**: {similarity.get('score', 0)}/100
- **Summary**: {similarity.get('summary', 'N/A')}
- **Common Elements**: {', '.join(similarity.get('common_elements', []))}
- **Evidence Patents**: {', '.join(similarity.get('evidence', []))}

### [2. 침해 리스크] Infringement Risk
- **Risk Level**: {infringement.get('risk_level', 'unknown').upper()}
- **Summary**: {infringement.get('summary', 'N/A')}
- **Risk Factors**:
{risk_factors_md}
- **Evidence Patents**: {', '.join(infringement.get('evidence', []))}

### [3. 회피 전략] Avoidance Strategy
- **Summary**: {avoidance.get('summary', 'N/A')}
- **Strategies**:
{strategies_md}
- **Alternatives**: {', '.join(avoidance.get('alternatives', []))}

---

## 📌 Conclusion
{analysis.get('conclusion', 'N/A')}

---

## 📚 Referenced Patents
"""
    for patent in result.get("search_results", []):
        md += f"""
### {patent.get('patent_id')}
- **Title**: {patent.get('title')}
- **Score**: {patent.get('grading_score', 0):.2f} (RRF: {patent.get('rrf_score', 0):.4f})
- **Abstract**: {patent.get('abstract')}
"""
    return md
