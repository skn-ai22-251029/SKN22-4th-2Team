"""
Utility functions for the Short-Cut Patent Analysis App.
State-less helper functions.

로깅 유틸리티(JsonLineFormatter, LogEvent)와 Streamlit UI 헬퍼를 포함합니다.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st


# =============================================================================
# 구조화 JSON 로그 포맷터 (CloudWatch / ELK 연동용)
# =============================================================================

class JsonLineFormatter(logging.Formatter):
    """extra 필드를 포함한 JSON 라인 포맷터.

    표준 logging.Formatter는 extra 딕셔너리를 출력하지 않으므로,
    이 포맷터를 핸들러에 부착하면 모든 로그가 JSON 한 줄로 직렬화됩니다.
    """

    # logging.LogRecord의 기본 속성 키 — extra 필드만 추출하기 위한 제외 목록
    _STANDARD_KEYS: set = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
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
    CUTOFF_FILTER = "cutoff_filter"
    HIGH_CUTOFF_WARNING = "high_cutoff_ratio_warning"
    ANALYSIS_CUTOFF = "analysis_cutoff_filter"

def get_risk_color(risk_level: str) -> tuple:
    """Get color scheme based on risk level."""
    colors = {
        "high": ("#dc3545", "🔴", "metric-high"),
        "medium": ("#ffc107", "🟡", "metric-medium"),
        "low": ("#28a745", "🟢", "metric-low"),
    }
    return colors.get(risk_level.lower(), ("#6c757d", "⚪", "metric-low"))


def get_score_color(score: int) -> str:
    """Get color based on similarity score."""
    if score >= 70:
        return "#dc3545"
    elif score >= 40:
        return "#ffc107"
    else:
        return "#28a745"


def get_patent_link(patent_id: str) -> str:
    """Generate Google Patents link from patent ID."""
    # Clean patent ID (remove spaces, dashes for URL)
    clean_id = patent_id.replace(" ", "").replace("-", "")
    return f"https://patents.google.com/patent/{clean_id}"


def display_patent_with_link(patent_id: str):
    """Display patent ID with clickable link."""
    link = get_patent_link(patent_id)
    st.markdown(f"📄 `{patent_id}` [🔗 원문 보기]({link})")


def format_analysis_markdown(result: dict) -> str:
    """Format analysis result as downloadable markdown."""
    analysis = result.get("analysis", {})
    
    md = f"""# ⚡ 쇼특허 (Short-Cut) Analysis Report
> Generated: {result.get('timestamp', datetime.now().isoformat())}
> Search Type: {result.get('search_type', 'hybrid').upper()}

## 💡 User Idea
{result.get('user_idea', 'N/A')}

---

## 📊 Analysis Summary

### [1. 유사도 평가] Similarity Assessment
- **Score**: {analysis.get('similarity', {}).get('score', 0)}/100
- **Summary**: {analysis.get('similarity', {}).get('summary', 'N/A')}
- **Common Elements**: {', '.join(analysis.get('similarity', {}).get('common_elements', []))}
- **Evidence Patents**: {', '.join(analysis.get('similarity', {}).get('evidence', []))}

### [2. 침해 리스크] Infringement Risk
- **Risk Level**: {analysis.get('infringement', {}).get('risk_level', 'unknown').upper()}
- **Summary**: {analysis.get('infringement', {}).get('summary', 'N/A')}
- **Risk Factors**:
{chr(10).join(['  - ' + f for f in analysis.get('infringement', {}).get('risk_factors', [])])}
- **Evidence Patents**: {', '.join(analysis.get('infringement', {}).get('evidence', []))}

### [3. 회피 전략] Avoidance Strategy
- **Summary**: {analysis.get('avoidance', {}).get('summary', 'N/A')}
- **Strategies**:
{chr(10).join(['  - ' + s for s in analysis.get('avoidance', {}).get('strategies', [])])}
- **Alternatives**: {', '.join(analysis.get('avoidance', {}).get('alternatives', []))}

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
