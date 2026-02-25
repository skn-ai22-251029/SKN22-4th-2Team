# 🔍 수석 아키텍트 코드 리뷰 #1
**리뷰 대상**: Dockerfile(멀티 스테이지 빌드) · FastAPI 백엔드 마이그레이션  
**리뷰 일자**: 2026-02-25  
**리뷰어**: Chief Architect / DevSecOps  
**대상 파일**:
- `Dockerfile`
- `.dockerignore`
- `requirements-api.txt`
- `main.py`
- `src/analysis_logic.py`
- `src/patent_agent.py`
- `src/reranker.py`

---

### 🔍 총평 (Architecture Review)

멀티 스테이지 빌드, non-root 사용자 실행, HEALTHCHECK, `.dockerignore` 보안 설정까지 프로덕션 수준의 Dockerfile 구조를 잘 갖추었으며, FastAPI 전환(Stateless화)의 방향도 올바르다.
다만, **CORS 와일드카드 허용**, **OpenAI API 타임아웃 미설정**, **Reranker의 동기 블로킹**, **`on_event` deprecation**, **`--no-cache-dir` 위치 오류(builder 레이어 최적화 손실)** 등 실 운영 시 치명적 또는 잠재적 문제가 될 항목들이 다수 발견되었다. Critical 항목 수정 후 머지할 것을 권고한다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)

*(아래 내용을 복사해서 Backend / DevOps 에이전트에게 전달하세요)*

---

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `main.py:27` — **CORS `allow_origins=["*"]` + `allow_credentials=True` 조합 금지**  
  `credentials=True`와 `allow_origins=["*"]`를 동시에 사용하면 브라우저가 요청을 거부하며, 보안적으로도 모든 도메인에서 인증 쿠키를 허용하는 치명적 취약점입니다.  
  → 환경 변수로 허용 Origin 목록을 관리하도록 수정하세요.
  ```python
  # 수정 예시
  import os
  ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
  app.add_middleware(
      CORSMiddleware,
      allow_origins=ALLOWED_ORIGINS,  # 명시적 도메인 목록
      allow_credentials=True,
      allow_methods=["GET", "POST"],
      allow_headers=["*"],
  )
  ```

- `src/patent_agent.py:288,305,330,550,621,714` — **OpenAI API 호출부 전체에 `timeout` 미설정**  
  네트워크 지연이나 OpenAI 서버 응답 지연 시 요청이 무한 대기하여 이벤트 루프가 영구 점유됩니다. ECS/K8s 헬스체크 실패 및 서비스 행(hang) 장애로 이어집니다.  
  → `AsyncOpenAI` 클라이언트 생성 시 또는 개별 API 호출 시 `timeout` 파라미터를 반드시 추가하세요.
  ```python
  # 수정 예시 - __init__에서 전역 타임아웃 설정 (권장)
  from openai import AsyncOpenAI
  import httpx
  self.client = AsyncOpenAI(
      api_key=OPENAI_API_KEY,
      timeout=httpx.Timeout(60.0, connect=10.0)  # 전체 60초, 연결 10초
  )
  ```

- `src/analysis_logic.py:113` — **`reranker.rerank()`가 동기 메서드인데 async 이벤트 루프에서 직접 호출**  
  `reranker.rerank()`는 `src/reranker.py`에서 `self.model.predict(pairs)`(CPU 블로킹 연산)를 동기적으로 실행합니다. 이를 async 함수 내에서 직접 호출하면 uvicorn의 이벤트 루프가 블로킹되어 동시 요청 처리 불가 상태가 됩니다.  
  → `asyncio.get_event_loop().run_in_executor()` 또는 `asyncio.to_thread()`로 래핑하세요.
  ```python
  # 수정 예시
  import asyncio
  reranked_docs = await asyncio.to_thread(
      reranker.rerank, user_idea, docs_for_rerank, top_k=5
  )
  ```

- `Dockerfile:24-26` — **가상환경(`venv`) 생성 후 pip upgrade와 install이 같은 `RUN` 레이어에 있으나, `--no-cache-dir`이 venv 생성 명령과 분리되지 않아 레이어 캐시 무효화 문제 발생 가능**  
  더 심각한 것은 `pip install --upgrade pip`와 패키지 설치가 하나의 `&&` 체인으로 묶여 있어, `requirements-api.txt`가 변경되지 않아도 `pip upgrade` 버전이 달라지면 전체 레이어가 재빌드됩니다.  
  → `pip upgrade`와 패키지 설치를 별도 레이어로 분리하거나, pip 버전을 고정하세요.
  ```dockerfile
  # 수정 예시
  RUN python -m venv /install
  RUN /install/bin/pip install --no-cache-dir --upgrade pip==24.0
  RUN /install/bin/pip install --no-cache-dir -r requirements-api.txt
  ```

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `main.py:37` — **`@app.on_event("startup")` deprecated (FastAPI 0.93+)**  
  FastAPI 0.93 이상에서는 `on_event`가 deprecated되고 `lifespan` context manager가 권장됩니다. `requirements-api.txt`에서 `fastapi>=0.111.0`을 명시했으므로 반드시 `lifespan` 패턴으로 전환해야 장기적 호환성이 보장됩니다.
  ```python
  # 수정 예시
  from contextlib import asynccontextmanager
  
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      global db_client, history_manager
      db_client = PineconeClient(skip_init_check=True)
      history_manager = HistoryManager()
      yield
      # 종료 시 정리 로직 가능
  
  app = FastAPI(lifespan=lifespan, ...)
  ```

- `main.py:56` — **`AnalyzeRequest.ipc_filters: list[str] = None` — Pydantic v2 타입 힌트 불일치**  
  Pydantic v2에서 `list[str] = None`은 타입 에러를 유발합니다. `Optional[List[str]] = None` 또는 `list[str] | None = None`으로 명확히 선언하세요.
  ```python
  from typing import Optional, List
  ipc_filters: Optional[List[str]] = None
  ```

- `src/patent_agent.py:433-436` — **동일한 로그 라인 중복 출력**  
  `logger.info(f"Detected target patents in query: {target_ids}")`가 두 번 연속 호출됩니다. 코드 리팩토링 중 복사-붙여넣기 오류로 보입니다. 한 줄 삭제하세요.

- `src/analysis_logic.py:147` — **`agent.critical_analysis()` 는 스트리밍 완료 후 동일 문서에 대해 LLM을 한 번 더 호출 (이중 과금)**  
  Step 5에서 `critical_analysis_stream()`으로 스트리밍한 결과를 구조화된 JSON으로도 따로 받기 위해 `critical_analysis()`를 추가 호출합니다. 동일 입력에 대해 GPT-4o를 **두 번** 호출하여 비용과 지연을 2배로 증가시킵니다. 스트리밍 중에 JSON을 파싱하거나, 구조화 응답 방식을 통일하는 것을 권장합니다.

- `.dockerignore:58` — **`*.json` 제외가 `project_items.json` 등 코드에서 사용하는 JSON 파일까지 차단할 수 있음**  
  `src/` 하위의 설정 파일이나 데이터 파일 중 JSON 형식이 있다면 컨테이너에 포함되지 않아 런타임 오류가 발생할 수 있습니다. 패턴을 `src/data/*.json` 등 경로 한정적으로 좁히거나, 실제로 필요한 파일을 예외 처리(`!src/config/*.json`)하는 것을 검토하세요.

- `Dockerfile:67` — **HEALTHCHECK에 `curl` 또는 `wget` 없이 Python 인라인 코드 사용**  
  현재 방식도 동작하지만, Python 인터프리터를 매 30초마다 새로 기동하므로 메모리와 CPU 오버헤드가 있습니다. 런타임 이미지에 `curl`을 최소 추가하거나, uvicorn의 헬스체크를 별도 경량 스크립트로 분리하는 것을 고려하세요.

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `src/analysis_logic.py:13-25` — **모듈 레벨 `_RERANKER_INSTANCE` 글로벌 싱글톤 패턴이 멀티 워커 환경에서 비효율적**  
  현재 `--workers 1`로 단일 워커이므로 당장 문제는 없으나, 향후 수평 확장 시 각 프로세스가 개별적으로 모델을 로드합니다. FastAPI의 `lifespan`으로 이관하여 앱 수명주기와 일치시키는 것이 더 명확합니다.

- `src/patent_agent.py:56` — **`OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")` 빈 문자열 기본값**  
  빈 문자열로 `AsyncOpenAI`를 초기화하면 실제 API 호출 시점(런타임)에 에러가 발생합니다. `__init__`에서 `if not OPENAI_API_KEY: raise ValueError`로 조기 실패(Fail-Fast)하는 로직이 이미 있지만, 모듈 import 시점에 경고 로그를 추가하면 디버깅이 용이합니다.

- `requirements-api.txt:70` — **`spacy>=3.7.0` 포함 — 실제 사용 여부 재확인 필요**  
  spaCy는 설치 용량이 크고, 실제 모델 다운로드(`python -m spacy download`)가 Dockerfile에 없으면 런타임 모델 로드 시 실패합니다. API 서버에서 spaCy를 직접 사용하는지 확인하고, 불필요하다면 제거하여 이미지 크기를 줄이세요.

- `Dockerfile:51-52` — **`COPY main.py .` 와 `COPY src/ ./src/` 를 별도 레이어로 분리한 점은 Good**  
  다만, `src/` 내부에 변경이 없어도 `main.py`만 수정하면 `src/` 레이어 이후의 레이어가 재실행됩니다. `src/`를 먼저 COPY하고 `main.py`를 나중에 COPY하면 레이어 캐시 효율을 높일 수 있습니다.
  ```dockerfile
  COPY src/ ./src/
  COPY main.py .
  ```

---

### 💡 Tech Lead의 머지(Merge) 권고

- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 항목이 수정되기 전까지 머지를 보류하세요.**

> **필수 수정 항목 요약 (머지 전 Blocker)**:
> 1. `main.py` — CORS `allow_origins=["*"]` + `allow_credentials=True` 조합 제거, 환경 변수 기반 Origin 관리로 교체
> 2. `src/patent_agent.py` — `AsyncOpenAI` 클라이언트에 `timeout` 설정 추가
> 3. `src/analysis_logic.py` — `reranker.rerank()` 동기 블로킹 → `asyncio.to_thread()` 래핑
> 4. `Dockerfile` — `pip upgrade` 레이어 분리 및 버전 고정
