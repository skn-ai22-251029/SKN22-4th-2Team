# Issue #18 — 컷오프(score < 0.3) 필터링된 특허 수 명시적 로깅

## 작업 개요
- **날짜**: 2026-02-26
- **담당**: Backend Agent
- **우선순위**: Medium
- **Epic**: 모니터링 / RAG 고도화

---

## 변경 파일

### `src/patent_agent.py`

### 변경 함수 및 내용

#### 1. `grade_results()` — JSON 구조화 로그 추가

그레이딩 점수 부여 완료 직후, `CUTOFF_THRESHOLD = 0.3` 기준으로 필터링 전/후 특허 수를 집계하여 구조화된 JSON 형태로 로깅한다.

```python
log_payload = {
    "event": "cutoff_filter",
    "before_filter": total_count,
    "after_filter": passed_count,
    "filtered_out": filtered_out,
    "filter_ratio_pct": round(filter_ratio * 100, 1),
    "threshold": 0.3,
    "average_grading_score": round(grading_response.average_score, 3),
}
# 80% 초과 시 WARNING, 이하 시 INFO
```

- 정상 범위: `logger.info("컷오프 필터링 결과", extra=log_payload)`
- 품질 저하 감지: `logger.warning("... 80%% 초과 ...", extra=log_payload)`

---

#### 2. `search_with_grading()` — rewrite 트리거 연동 경고

`grade_results()` 반환 직후, 컷오프 비율을 재계산하여 rewrite 자동 트리거 여부와 함께 `WARNING` 로그 발행.

```python
extra={
    "event": "high_cutoff_ratio_warning",
    "before_filter": _total,
    "after_filter": _passed,
    "filter_ratio_pct": ...,
    "rewrite_trigger_threshold": GRADING_THRESHOLD,
    "will_rewrite": grading.average_score < GRADING_THRESHOLD,
}
```

---

#### 3. `critical_analysis()` — 분석 진입 전 필터 통계

분석 단계에서 실제로 컨텍스트로 사용될 특허 수를 `stage: critical_analysis` 레이블로 로깅.

---

#### 4. `critical_analysis_stream()` — 스트리밍 버전 동일 패턴

`stage: critical_analysis_stream` 레이블로 동일 JSON 구조 로깅.

---

## 로그 이벤트 종류

| `event` 값 | 발행 위치 | 레벨 |
|---|---|---|
| `cutoff_filter` | `grade_results()` | INFO / WARNING |
| `high_cutoff_ratio_warning` | `search_with_grading()` | WARNING |
| `analysis_cutoff_filter` (stage=critical_analysis) | `critical_analysis()` | INFO / WARNING |
| `analysis_cutoff_filter` (stage=critical_analysis_stream) | `critical_analysis_stream()` | INFO / WARNING |

---

## 80% 임계값 의미

| 필터링 비율 | 해석 | 액션 |
|---|---|---|
| 0~80% | 정상 검색 품질 | INFO 로그만 발행 |
| 80% 초과 | 검색 품질 저하 의심 | WARNING 에스컬레이션, 쿼리 rewrite 고려 |

---

## 기대 효과
- 검색 품질 지표 실시간 파악 (CloudWatch / ELK 등에서 `event: cutoff_filter` 필터링 가능)
- JSON `extra` 필드로 구조화되어 있어 메트릭 집계 및 알림 자동화 용이
- `filter_ratio_pct` 추이로 컷오프 임계값 튜닝 근거 데이터 확보
- `will_rewrite` 필드로 rewrite 자동 대응 여부 사전 추적 가능
