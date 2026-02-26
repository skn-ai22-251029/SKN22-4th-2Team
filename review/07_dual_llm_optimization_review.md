# 🔍 Issue #14 — 이중 LLM 호출 비용 절감 코드 리뷰

> 리뷰 일시: 2026-02-26  
> 대상 문서: `backend/07_dual_llm_optimization.md`  
> 대상 파일: `src/patent_agent.py`, `src/analysis_logic.py`

---

### 🔍 총평 (Architecture Review)

아키텍처적으로 **올바른 방향의 최적화**입니다. 스트리밍 결과를 재활용하여 2차 GPT-4o 호출을 경량 파싱으로 교체하는 설계는 비용 효율적이며, 기존 `critical_analysis()` 메서드를 보존하여 독립 파이프라인(`analyze()`)의 호환성도 유지했습니다. 다만, **PARSING_MODEL 기본값이 문서와 코드 간 불일치하는 치명적 설정 오류**가 발견되어 실제 비용 절감 효과가 발생하지 않고 있습니다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Backend 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `patent_agent.py:67` — **PARSING_MODEL 기본값이 `gpt-4o`로 설정되어 비용 절감 효과가 전혀 없음.**
  - 문서(`07_dual_llm_optimization.md` 22행)에는 `GPT-4o-mini`를 사용한다고 명시했으나, 실제 코드는 `PARSING_MODEL = os.environ.get("PARSING_MODEL", "gpt-4o")`로 되어 있어 **기본값이 GPT-4o**입니다.
  - `.env`에 `PARSING_MODEL=gpt-4o-mini`를 별도로 설정하지 않는 한, 기존과 동일하게 GPT-4o가 2번 호출되어 비용 절감이 0%입니다.
  - **수정 제안:**
    ```python
    # 수정 전
    PARSING_MODEL = os.environ.get("PARSING_MODEL", "gpt-4o")
    # 수정 후
    PARSING_MODEL = os.environ.get("PARSING_MODEL", "gpt-4o-mini")
    ```

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `patent_agent.py:1052` — **`timeout=30.0` 파라미터가 OpenAI Python SDK에서 예상대로 동작하지 않을 수 있음.**
  - `AsyncOpenAI.chat.completions.create()`의 `timeout` 파라미터는 `openai` SDK v1.x에서 `httpx.Timeout` 객체를 기대합니다. `float` 값을 전달하면 전체 요청 타임아웃으로 적용되긴 하나, 이미 클라이언트 레벨(`__init__`의 200~202행)에서 60초 타임아웃이 설정되어 있으므로 **중복 설정**입니다.
  - 파싱 작업은 입력 토큰 대비 출력이 작으므로 30초면 충분하지만, 클라이언트 레벨 타임아웃(60초)과의 관계를 주석으로 명시하는 것을 권장합니다.

- `patent_agent.py:968-1062` — **파싱 실패 시 폴백이 `_empty_analysis()`로만 처리되어 사용자에게 '분석 결과 없음'으로 표시될 수 있음.**
  - `critical_analysis()`는 실패 시 `FALLBACK_MODEL`(gpt-3.5-turbo)로 재시도하는 2단계 폴백을 갖추고 있으나, `parse_streaming_to_structured()`는 1단계 폴백(빈 결과 반환)만 있습니다.
  - 스트리밍은 이미 성공한 상태이므로 파싱만 실패하는 경우, `FALLBACK_MODEL`로 한 번 더 시도하면 사용자 경험을 개선할 수 있습니다. 다만 이는 즉시 필요한 수정은 아니며 **향후 개선 사항**입니다.

- `analysis_logic.py:149-151` — **`streamed_text`가 빈 문자열이 될 수 있는 경로에 대한 방어가 `parse_streaming_to_structured()` 내부에만 존재.**
  - 148행에서 `stream_full` 이벤트를 놓치는 경우(예: 스트리밍 중 네트워크 에러) `streamed_text`가 빈 문자열인 채로 전달됩니다. `parse_streaming_to_structured()` 988행에서 빈 입력 체크가 되어 있으므로 안전하지만, 호출부에서도 빈 텍스트 여부를 로깅하면 디버깅이 용이해집니다.

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `patent_agent.py:67` — **`PARSING_MODEL` 주석이 부정확.**
  - 현재 주석: `# 스트리밍 결과 → JSON 변환용 모델` — 역할은 맞으나 "경량 파싱용"이라는 의도를 명시하면 향후 유지보수 시 기본값 변경 의도를 더 명확히 전달할 수 있습니다.
  - 제안: `# 스트리밍 마크다운 → JSON 구조화 파싱용 경량 모델 (비용 절감 목적)`

- `patent_agent.py:993` — **`patent_ids` 생성 로직이 `critical_analysis_stream()`의 `relevant_results` 필터링 로직(778행)과 동일한 기준(0.3 이상, 상위 5개)을 사용하나 별도로 구현됨.**
  - 동일한 필터링 기준이 3곳(700행, 778행, 993행)에 중복되므로, 향후 임계값 변경 시 하나만 빠뜨리면 불일치가 발생할 수 있습니다. 상수화(`MIN_ANALYSIS_SCORE = 0.3`)를 고려하세요.

- `analysis_logic.py:150` — **주석이 정확하고 변경 이유가 명시되어 있어 좋습니다.** `# 기존: GPT-4o 2차 호출 → 최적화: GPT-4o-mini 파싱 (비용 ~50% 절감)` — 다만 `PARSING_MODEL` 기본값이 수정되기 전까지는 이 주석이 사실과 다릅니다.

---

### 📐 수정 필요성 평가: 정말 필요한 수정이었는가?

| 평가 항목 | 판정 |
|-----------|------|
| **비즈니스 가치** | ✅ 분석 1건당 ~50% API 비용 절감은 유의미 |
| **아키텍처 합리성** | ✅ 스트리밍 텍스트 재활용 → 경량 파싱은 합리적 설계 |
| **기존 코드 영향도** | ✅ `critical_analysis()` 보존, `analyze()` 파이프라인 무영향 |
| **구현 품질** | ⚠️ PARSING_MODEL 기본값 오류로 **의도된 효과 미달성** |

> **결론**: 수정 자체는 **적절하고 필요한 최적화**이나, **PARSING_MODEL 기본값 설정 오류**로 인해 현재 배포 시 비용 절감이 실제로 발생하지 않습니다.

---

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 항목이 수정되기 전까지 머지를 보류하세요.**
  - `patent_agent.py:67`의 `PARSING_MODEL` 기본값을 `"gpt-4o-mini"`로 수정한 후 머지하세요.
