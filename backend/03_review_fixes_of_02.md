# [코드 리뷰 반영] Dockerfile · FastAPI 백엔드 수정사항 적용

## 리뷰 출처
`review/01_dockerfile_and_backend_review.md` — 수석 아키텍트 / DevSecOps 리뷰 (2026-02-25)

---

## 1. 완료한 작업 내역

### 🔴 Critical (머지 블로커 → 전부 수정 완료)

| # | 파일 | 문제 | 조치 |
|---|------|------|------|
| 1 | `main.py` | CORS `allow_origins=["*"]` + `credentials=True` 보안 취약점 | 환경 변수 `ALLOWED_ORIGINS`로 허용 Origin 관리하도록 변경 |
| 2 | `src/patent_agent.py` | `AsyncOpenAI` 타임아웃 미설정 → 이벤트 루프 무한 점유 | `httpx.Timeout(60.0, connect=10.0)` 전역 설정 추가 |
| 3 | `src/analysis_logic.py` | `reranker.rerank()` 동기 블로킹으로 이벤트 루프 차단 | `asyncio.to_thread()`로 래핑하여 비동기 처리 |
| 4 | `Dockerfile` | pip upgrade + 패키지 설치가 동일 레이어 → 캐시 무효화 | `RUN python -m venv`, `pip install pip==24.0`, `pip install -r` 3단계로 분리 |

### 🟡 Warning (개선 권장 → 적용 완료)

| # | 파일 | 문제 | 조치 |
|---|------|------|------|
| 5 | `main.py` | `@app.on_event("startup")` deprecated | `@asynccontextmanager lifespan` 패턴으로 전환 |
| 6 | `main.py` | `ipc_filters: list[str] = None` Pydantic v2 타입 불일치 | `Optional[List[str]] = None`으로 수정 |
| 7 | `src/patent_agent.py` | 동일 로그 메시지 2회 중복 출력 | 중복 `logger.info` 제거 |
| 8 | `.dockerignore` | `*.json` 와일드카드가 src/ 설정 JSON 차단 가능 | `src/data/*.json` 경로 한정 패턴으로 변경 |

### 🟢 Info (클린 코드 → 적용 완료)

| # | 파일 | 조치 |
|---|------|------|
| 9 | `Dockerfile` | `COPY src/` → `COPY main.py` 순서 변경으로 레이어 캐시 효율 개선 |
| 10 | `src/patent_agent.py` | `OPENAI_API_KEY` 빈 문자열일 때 import 시점 `logger.warning()` 추가 |

---

## 2. 다음 단계 권장 사항
- Critical 항목 전부 수정 완료 → DevOps 에이전트에게 머지 및 빌드 검증 요청 가능
- Warning 중 `src/analysis_logic.py:147` 이중 LLM 호출 비용 절감은 향후 스트리밍 응답 구조화 작업 시 함께 처리 권장 (별도 이슈 등록 필요)

## 3. PM 에이전트 상태 업데이트
- Issue #6 코드 리뷰 반영 완료, 머지 블로커 해제됨
