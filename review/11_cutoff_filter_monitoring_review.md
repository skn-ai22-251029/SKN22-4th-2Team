# 🔍 Code Review: Issue #18 — 컷오프 필터 모니터링 로깅

- **리뷰 일시**: 2026-02-26
- **리뷰어**: Senior Architect (Reviewer Agent)
- **대상 파일**: `src/patent_agent.py`
- **관련 문서**: `backend/11_cutoff_filter_monitoring.md`

---

### 🔍 총평 (Architecture Review)

구현 의도(컷오프 필터링 가시성 확보)는 명확하고 로그 페이로드 구조도 CloudWatch/ELK 연동을 고려한 JSON-ready 형식으로 잘 설계되었습니다.
그러나 **동일한 컷오프 계산 로직이 4곳에 복사·붙여넣기**되어 있어, 임계값 변경 시 일관성 오류가 발생할 수 있는 구조적 DRY 위반이 핵심 문제입니다.
또한 Python 표준 `logging` 모듈이 `extra` 딕셔너리를 JSON으로 직렬화해 주지 않으므로 **"구조화 JSON 로그"라는 목표가 실제로 달성되지 않고 있습니다.**

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Backend 에이전트에게 전달하세요)*

---

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `patent_agent.py:598, 702, 763, 867` — **동일 컷오프 로직 4중 중복 (DRY 위반)**
  - `CUTOFF_THRESHOLD = 0.3` 상수 및 필터 비율 계산 코드(`sum(1 for r in results if r.grading_score >= X)`)가 `grade_results()`, `search_with_grading()`, `critical_analysis()`, `critical_analysis_stream()` 총 4곳에 복사되어 있습니다.
  - **위험**: 임계값을 0.3 → 0.4로 바꾸려 할 때 누락된 복사본이 발생하면 파이프라인 운영 중 로그 불일치 및 rewrite 트리거 오판이 생깁니다.
  - **해결**: 파일 최상단 전역 상수로 통일하거나 private 헬퍼 메서드로 추출하세요.
  ```python
  # patent_agent.py 전역 상수 영역 (69~72번 줄 기존 THRESHOLD 상수들과 함께)
  CUTOFF_THRESHOLD: float = float(os.environ.get("CUTOFF_THRESHOLD", "0.3"))

  # PatentAgent 내부 헬퍼 (재사용)
  def _compute_filter_stats(
      self,
      results: List[PatentSearchResult],
      threshold: float = CUTOFF_THRESHOLD,
  ) -> dict:
      total = len(results)
      passed = sum(1 for r in results if r.grading_score >= threshold)
      filtered = total - passed
      ratio = (filtered / total) if total > 0 else 0.0
      return {
          "before_filter": total,
          "after_filter": passed,
          "filtered_out": filtered,
          "filter_ratio_pct": round(ratio * 100, 1),
          "threshold": threshold,
      }
  ```

- `patent_agent.py:49~50` — **표준 `logging.basicConfig`는 `extra` 필드를 JSON으로 직렬화하지 않습니다**
  - 현재 구조에서 `logger.info("...", extra=log_payload)` 호출 시 `extra` 딕셔너리 값들은 콘솔에 기본 포맷(`%(message)s`)으로는 **출력되지 않습니다.** CloudWatch Agent가 텍스트 로그를 수집할 경우 JSON 필드가 누락됩니다.
  - **해결**: `python-json-logger` 패키지를 도입하거나, `StructuredLogFormatter`를 `utils.py`에 구현하여 `extra` 필드가 JSON 라인으로 출력되도록 설정하세요.
  ```python
  # src/utils.py에 추가
  import json, logging

  class JsonLineFormatter(logging.Formatter):
      def format(self, record: logging.LogRecord) -> str:
          log_obj = {
              "timestamp": self.formatTime(record),
              "level": record.levelname,
              "logger": record.name,
              "message": record.getMessage(),
          }
          # extra 필드 병합
          std_keys = logging.LogRecord("","",0,"","").__dict__.keys()
          for k, v in record.__dict__.items():
              if k not in std_keys:
                  log_obj[k] = v
          return json.dumps(log_obj, ensure_ascii=False)
  ```

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `patent_agent.py:614, 707, 780, 884` — **`%%` 이스케이프 일관성 문제**
  - f-string이 아닌 일반 문자열(`"... 80%% ..."`)에서 `%%`는 `%`로 치환되지만, 이 맥락에서는 `%`로 직접 써야 의도가 명확합니다. f-string 내부라면 `%%`가 맞지만, 일반 문자열에서 `%%`는 `logging` 모듈의 `%` 포맷 처리 잔재입니다. 가독성 혼란 요소이므로 `80%`로 통일하는 것을 권장합니다.

- `patent_agent.py:702~720` — **`search_with_grading()`에서 컷오프 비율을 재계산하는 것은 중복 연산**
  - `grade_results()` 내부에서 이미 동일한 계산과 로그를 발행합니다. 이 블록은 `grade_results()`가 반환한 통계를 활용하도록 리팩토링하거나, `GradingResponse`에 `filter_stats` 필드를 추가하여 전달하는 방식이 더 효율적입니다.
  ```python
  class GradingResponse(BaseModel):
      results: List[GradingResult]
      average_score: float
      filter_stats: dict = Field(default_factory=dict)  # 컷오프 통계 전달
  ```

- `patent_agent.py:598` — **`CUTOFF_THRESHOLD` 상수가 환경 변수로 제어되지 않음**
  - `GRADING_THRESHOLD`(L70)는 `os.environ.get()`으로 외부 주입이 가능하지만, 로깅 블록에서 사용하는 `CUTOFF_THRESHOLD = 0.3`은 하드코딩입니다. 프로덕션에서 임계값 튜닝 시 코드 배포가 필요해질 수 있습니다.

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `patent_agent.py:604~622` — 로그 이벤트 키 문자열(`"cutoff_filter"`, `"high_cutoff_ratio_warning"`, `"analysis_cutoff_filter"`)을 Enum 또는 상수로 선언하면 오타 방지 및 검색 가용성이 향상됩니다.
  ```python
  class LogEvent:
      CUTOFF_FILTER = "cutoff_filter"
      HIGH_CUTOFF_WARNING = "high_cutoff_ratio_warning"
      ANALYSIS_CUTOFF = "analysis_cutoff_filter"
  ```

- `src/utils.py` — 현재 파일은 **Streamlit UI 유틸리티만** 포함하고 있습니다. 태스크 명세서에서 "로깅 유틸리티"를 `utils.py`에 구현하라고 명시했으나, 현재 없습니다. `JsonLineFormatter` 및 `_compute_filter_stats` 헬퍼를 이곳에 위치시키면 `patent_agent.py`의 책임 범위가 명확해집니다.

- `backend/11_cutoff_filter_monitoring.md` — 문서 내 `CUTOFF_THRESHOLD` 값이 `0.3`으로 하드코딩된 예시 코드로 제시되어 있으나, 코드가 환경 변수화되면 문서도 함께 업데이트가 필요합니다.

---

### 💡 Tech Lead의 머지(Merge) 권고

- [ ] ~~이대로 Main 브랜치에 머지해도 좋습니다.~~
- [x] **Critical 항목이 수정되기 전까지 머지를 보류하세요.**

> **사유**: 로깅 코드 4중 복사 구조는 임계값 변경 시 운영 오류의 직접 원인이 됩니다. 또한 `extra` 필드가 실제 JSON으로 출력되지 않는 상태라면 "구조화 JSON 로그" 목표가 달성되지 않아, CloudWatch Metric Filter 등 후속 모니터링 자동화 작업이 모두 무효화됩니다. 두 Critical 항목 수정 후 재검토를 요청합니다.
