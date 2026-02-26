# 🛠️ Issue #18 — 컷오프 필터 모니터링 코드 리뷰 수정 (v2)

- **작업 일시**: 2026-02-26
- **대상 파일**: `src/patent_agent.py`, `src/utils.py`
- **관련 리뷰**: `review/11_cutoff_filter_monitoring_review.md`
- **상태**: ✅ 완료

---

## 📋 수정 항목 요약

### 🔴 Critical #1: DRY 위반 해결 — 컷오프 계산 로직 4중 복사 제거

**문제**: `CUTOFF_THRESHOLD = 0.3`과 `sum(1 for r in results if r.grading_score >= ...)` 블록이 
`grade_results()`, `search_with_grading()`, `critical_analysis()`, `critical_analysis_stream()` 4곳에 그대로 복사됨.

**수정 내용**:
1. `CUTOFF_THRESHOLD`를 **전역 상수(환경 변수)**로 선언 (`L71`)
   ```python
   CUTOFF_THRESHOLD = float(os.environ.get("CUTOFF_THRESHOLD", "0.3"))
   ```
2. `_compute_filter_stats()` private 헬퍼 추출 → 통계 계산 로직 단일화
3. `_log_filter_stats()` private 헬퍼 추출 → 로그 발행 로직 단일화
4. 4곳 모두 헬퍼 호출로 교체

### 🔴 Critical #2: `extra` 필드 JSON 직렬화 미적용 해결

**문제**: 표준 `logging.basicConfig()`는 `extra` 딕셔너리를 JSON으로 출력하지 않아, CloudWatch에서 구조화 필드 누락.

**수정 내용**:
1. `src/utils.py`에 `JsonLineFormatter` 클래스 구현
   - `logging.LogRecord`의 표준 키를 필터링하고 `extra` 필드만 JSON 객체에 병합
2. `configure_json_logging()` 유틸리티 함수 추가
   - 루트 로거에 `JsonLineFormatter` 자동 적용
3. `patent_agent.py`에서 `logging.basicConfig()` → `configure_json_logging()` 교체

### 🟡 Warning #1: `search_with_grading()` 중복 연산 제거

**문제**: `grade_results()` 내부에서 이미 계산한 필터 통계를 `search_with_grading()`에서 재계산.

**수정 내용**:
1. `GradingResponse` 모델에 `filter_stats: Dict[str, Any]` 필드 추가
2. `grade_results()`에서 통계를 `grading_response.filter_stats`에 설정
3. `search_with_grading()`에서 `grading.filter_stats` 재활용 → 이중 계산 제거

### 🟡 Warning #2: `%%` 이스케이프 통일

**문제**: f-string 환경에서 `80%%` 표기가 혼란 유발.

**수정 내용**: `_log_filter_stats()` 헬퍼에서 f-string으로 통일 → `80%` 직접 표기

### 🟢 Info: LogEvent 상수 클래스

**수정 내용**: `src/utils.py`에 `LogEvent` 상수 클래스 추가
```python
class LogEvent:
    CUTOFF_FILTER = "cutoff_filter"
    HIGH_CUTOFF_WARNING = "high_cutoff_ratio_warning"
    ANALYSIS_CUTOFF = "analysis_cutoff_filter"
```

---

## 📁 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `src/utils.py` | 수정 | `JsonLineFormatter`, `configure_json_logging()`, `LogEvent` 추가 |
| `src/patent_agent.py` | 수정 | 전역 `CUTOFF_THRESHOLD` 추가, 로깅 설정 교체, 4곳 DRY 리팩토링, `GradingResponse.filter_stats` 추가 |

---

## ✅ 검증 결과

- [x] `py_compile` 구문 검증 통과 (patent_agent.py, utils.py 모두)
- [x] 4곳 중복 로직 → 2개 헬퍼(`_compute_filter_stats`, `_log_filter_stats`)로 통합
- [x] `%%` 이스케이프 잔재 완전 제거
- [x] `extra` 필드가 JSON 라인으로 직렬화됨

---

## 📋 다음 단계 권장 사항

1. PR 후 재리뷰 요청 → Critical 항목 해소 확인
2. `backend/11_cutoff_filter_monitoring.md` 문서 내 `0.3` 하드코딩 예시 → 환경 변수 설명으로 업데이트
3. 통합 테스트에서 CloudWatch Metric Filter가 JSON 필드를 정상 인식하는지 확인

---

## 📌 PM 에이전트 전달용 상태 업데이트

> **Issue #18 (컷오프 필터 모니터링)**: 코드 리뷰 피드백 반영 완료.
> Critical 2건, Warning 2건, Info 1건 모두 수정됨.
> 구문 검증 통과. 재리뷰 후 머지 가능 상태.
