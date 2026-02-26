# [코드 리뷰] RAG 핵심 로직 모듈화 및 코드 품질 리팩토링 (#3)

> 리뷰 일시: 2026-02-26  
> 리뷰어: 수석 아키텍트 (Chief Architect & DevSecOps)  
> 작업 브랜치: `feature/rag-code-quality-refactoring`  
> 리뷰 대상 문서: `backend/14_rag_code_quality_refactoring.md`  
> 리뷰 대상 파일: `src/reranker.py`, `src/analysis_logic.py`, `src/utils.py`, `src/vector_db.py`, `src/patent_agent.py`

---

### 🔍 총평 (Architecture Review)

전반적으로 이번 리팩토링은 방향성이 옳고 완성도가 높다. PEP8 정렬, Type Hints 전면 도입, SRP 위반 해소(`utils.py`에서 Streamlit 의존성 제거), `frozenset` 적용, `asyncio.get_running_loop()` 전환, `time.monotonic()` 사용 등은 프로덕션 코드 기준을 충족하는 모범 사례다. 다만, 몇 가지 **런타임 안전성**과 **비동기 보안** 이슈가 남아있어 즉시 병합은 보류를 권고한다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Backend 에이전트에게 전달하세요)*

---

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `src/patent_agent.py:354~380` — **`generate_hypothetical_claim()` 타임아웃/예외 처리 누락**  
  `critical_analysis_stream()`, `grade_results()` 등은 `try-except`로 보호되어 있지만, `generate_hypothetical_claim()`와 `embed_text()`는 **예외 처리 없이 그대로 노출**되어 있다. OpenAI API 타임아웃 또는 네트워크 오류 발생 시 전체 파이프라인이 `Exception`으로 종료된다.
  ```python
  # 수정 방향 예시
  try:
      response = await self.client.chat.completions.create(...)
  except Exception:
      logger.exception("HyDE 청구항 생성 실패. 원본 아이디어를 폴백으로 반환합니다.")
      return user_idea  # 폴백: 원본 아이디어를 그대로 검색 쿼리로 사용
  ```

- `src/patent_agent.py:945~958` — **`critical_analysis_stream()` 스트리밍 루프 예외 처리 없음**  
  `async for chunk in response:` 블록에 `try-except`가 없다. 스트리밍 도중 연결이 끊기면 `asyncio.CancelledError` 또는 `httpx.ReadTimeout`이 호출자(FastAPI SSE 엔드포인트 등)까지 전파된다. 스트리밍 제너레이터 내부에서 반드시 예외를 캐치해야 한다.
  ```python
  # 수정 방향 예시
  try:
      async for chunk in response:
          if chunk.choices[0].delta.content:
              yield chunk.choices[0].delta.content
  except Exception:
      logger.exception("스트리밍 중 오류 발생. 스트림을 종료합니다.")
      # 빈 yield로 제너레이터를 gracefully 종료
      return
  ```

- `src/analysis_logic.py:42~54` — **`_reranker_instance` 전역 싱글턴의 Thread Safety 미보장**  
  `run_full_analysis()`는 비동기 컨텍스트에서 병렬 호출될 수 있다. 두 코루틴이 동시에 `_reranker_instance is None` 조건을 통과하면 `Reranker()`가 **두 번 초기화**된다. 모델 로딩 비용이 크고, HuggingFace 모델에 따라 전역 상태를 오염시킬 수 있다.
  ```python
  # 수정 방향: asyncio.Lock() 사용
  _reranker_lock = asyncio.Lock()
  
  async def get_reranker() -> Optional[Any]:  # 동기 → 비동기 함수로 전환
      global _reranker_instance
      async with _reranker_lock:
          if _reranker_instance is None:
              # ... 기존 로직
  ```
  > ⚠️ 단, `get_reranker()`를 `async def`로 변경하면 `run_full_analysis()` 내 호출부도 `await get_reranker()`로 수정해야 한다.

- `src/vector_db.py:584~585` — **`pickle`을 이용한 메타데이터 캐시 저장 — Deserialization 보안 위험**  
  `pickle.dump / pickle.load`는 임의 코드 실행(Arbitrary Code Execution)이 가능한 알려진 보안 취약점이다. 공격자가 `pinecone_metadata.pkl` 파일을 교체할 수 있는 환경(컨테이너 볼륨 마운트, S3 sync 등)이라면 클래스 전체가 위험에 노출된다. `json` 또는 `msgpack`으로 대체를 강력히 권고한다.
  ```python
  # 수정 방향: json으로 대체
  import json
  with open(self.metadata_path.with_suffix(".json"), 'w', encoding='utf-8') as f:
      json.dump({"metadata": self.metadata}, f, ensure_ascii=False, default=str)
  ```

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `src/patent_agent.py:330~333` — **`@retry` 데코레이터의 `retry_if_exception_type(Exception)` 과도한 범위**  
  `Exception`을 통째로 재시도 대상으로 삼으면 `PromptInjectionError`, `ValidationError` 등 **비-일시적 오류**까지 재시도한다. 재시도 대상을 네트워크/API 관련 오류 타입으로 좁혀야 한다.
  ```python
  from openai import RateLimitError, APITimeoutError, APIConnectionError
  
  @retry(
      wait=wait_random_exponential(min=1, max=10),
      stop=stop_after_attempt(5),
      retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
  )
  ```

- `src/patent_agent.py:448~451` — **`_execute_search()` 제네릭 `Exception` 재시도**  
  위와 동일한 패턴. `Exception` 전체를 재시도하면 Pinecone API의 `4xx` 클라이언트 오류(잘못된 필터, 인덱스 없음 등)도 3회 재시도하며 불필요한 API 비용과 지연을 발생시킨다.

- `src/patent_agent.py:1263~1304` — **CLI `main()` 함수의 `input()` 블로킹 호출**  
  `asyncio.run(main())`으로 실행되는 비동기 루프 안에서 `input()`은 동기 블로킹 호출이다. 이는 이벤트 루프를 직접 점유한다. CLI 목적이라면 큰 문제는 아니지만, 이 파일이 FastAPI 앱과 같은 프로세스에서 임포트될 경우 혼용 위험이 있다.  
  → CLI 엔트리포인트를 별도 파일로 분리하거나 `asyncio.get_event_loop().run_in_executor()`를 활용 권장.

- `src/vector_db.py:169~173` — **`PineconeClient.__init__` 파라미터 타입 힌트 미완성**  
  `pinecone_config: PineconeConfig = None`, `embedding_dim: int = None`는 타입이 `Optional`이어야 한다. 이번 리팩토링에서 `ipc_filters`의 `Optional` 전환을 진행했으나 생성자 파라미터는 빠졌다.
  ```python
  def __init__(
      self,
      pinecone_config: Optional[PineconeConfig] = None,
      embedding_dim: Optional[int] = None,
      skip_init_check: bool = False,
  ):
  ```

- `src/patent_agent.py:1087~1088` — **`parse_streaming_to_structured()` user_prompt에 `wrap_user_query()` 미적용**  
  `grade_results()`, `generate_hypothetical_claim()`, `rewrite_query()` 등은 모두 `wrap_user_query(user_idea)` 태그를 사용하여 프롬프트 인젝션을 방어하고 있으나, `parse_streaming_to_structured()`의 `user_prompt`에서는 `user_idea`가 `<user_query>` 태그 없이 그대로 삽입되고 있다.
  ```python
  # 현재 (위험)
  user_prompt = f"""[사용자 아이디어]
  {user_idea}
  ...
  """
  # 수정 방향 (안전)
  user_prompt = f"""[사용자 아이디어]
  {wrap_user_query(user_idea)}
  ...
  """
  ```

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `src/patent_agent.py:40~45` — **`json_loads` / `json_dumps` 전역 함수 오버라이드 패턴 개선 권장**  
  `orjson` 분기 로직이 모듈 최상단에 직접 기술되어 있어 가독성을 해친다. `try-except` 블록을 별도 `_compat.py` 또는 `src/serialization.py`로 분리하거나, `importlib.util.find_spec("orjson")`를 사용하는 방식으로 정리하면 더 명확하다.

- `src/analysis_logic.py:280~332` — **`run_full_analysis()` 최종 결과 조합 시 `getattr` 남용**  
  `getattr(analysis.similarity, "score", 0)`, `getattr(r, "publication_number", ...)` 등 `getattr`를 방어적으로 사용하고 있으나, `CriticalAnalysisResponse`와 `PatentSearchResult`가 이미 Pydantic/dataclass로 스키마가 확정되어 있다. 불필요한 `getattr` 없이 직접 필드 접근이 오히려 런타임 오류를 명시적으로 드러내어 디버깅에 유리하다.

- `src/reranker.py:99~105` — **`rerank()` 내 `pairs` 리스트에 `claims` 미포함**  
  Cross-Encoder 입력 텍스트가 `title + abstract`만으로 구성되어 있다. 특허 유사도 판단에서 `claims`(청구항)는 핵심 텍스트인데 재정렬 시 제외되어 정확도가 낮아질 수 있다.
  ```python
  # 개선 제안
  f"{doc.get('title', '')} {doc.get('abstract', '')} {doc.get('claims', '')}"[:text_max_length]
  ```

- `src/utils.py:80~88` — **`LogEvent` 클래스에 `PIPELINE_START`, `PIPELINE_COMPLETE` 등 이벤트 상수 누락**  
  `patent_agent.py`에서 `"event": "pipeline_start"`, `"event": "search_done"` 등을 문자열 리터럴로 직접 사용하는 곳이 남아있다. `LogEvent` 상수로 전면 통일하면 CloudWatch Metric Filter 설정의 일관성이 높아진다.

- `src/utils.py:97~112` — **`_RISK_COLOR_MAP` 딕셔너리가 함수 호출마다 재생성됨**  
  `get_risk_color()` 내부에서 `_RISK_COLOR_MAP`을 매번 만드는 구조다. 함수 외부 모듈 레벨 상수로 올리거나 `functools.lru_cache`를 적용하면 약간의 성능 이득이 있다.

---

### 💡 Tech Lead의 머지(Merge) 권고

- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 항목이 수정되기 전까지 머지를 보류하세요.**

> **머지 보류 사유 요약:**  
> 1. `generate_hypothetical_claim()` / `embed_text()` 무방비 API 호출 → 파이프라인 전체 다운 위험  
> 2. `critical_analysis_stream()` 스트리밍 루프 예외 미처리 → FastAPI SSE 연결 시 서버 500 발생 가능  
> 3. `_reranker_instance` 글로벌 싱글턴 동시성 레이스 컨디션 → 부하 상황에서 재현 가능  
> 4. `pickle` 기반 메타데이터 캐시 → 프로덕션 보안 기준 미달  
> 5. `parse_streaming_to_structured()` 내 `wrap_user_query()` 누락 → 프롬프트 인젝션 방어 일관성 파괴  
>
> Warning 항목 중 `@retry` 범위는 API 비용 측면에서 즉시 수정을 강력히 권장하며, 나머지 Info 항목은 다음 PR에서 처리해도 무방합니다.
