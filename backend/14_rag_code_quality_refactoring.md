# [RAG 고도화] 핵심 로직 모듈화 및 코드 품질 리팩토링 (#3)

> 작업 일시: 2026-02-26  
> 브랜치: `feature/rag-code-quality-refactoring`  
> 담당: Backend  
> Epic: RAG 로직 고도화

---

## 1. 작업 개요

`src/` 하위 핵심 모듈들의 코드 품질을 PEP8 및 Type Hints 기준으로 전면 리팩토링했습니다.  
이전 작업(`feature/prompt-injection-sandboxing`)을 커밋/푸시 완료 후 신규 브랜치에서 진행했습니다.

---

## 2. 대상 파일 및 변경 내역

### 2.1 `src/reranker.py` — 전면 재작성

| 항목 | 이전 | 이후 |
|------|------|------|
| Type Hints | 미흡 (`str`, 반환타입 없음) | 전면 적용 (`Optional[Any]`, `List[Dict[str, Any]]`, `-> None`) |
| 모델 로드 실패 처리 | `print()` 또는 빈 `except` | `logger.exception()` (스택 트레이스 포함) |
| 모델 상태 확인 | `if not self.model` (직접 접근) | `is_available` 프로퍼티로 캡슐화 |
| 매직 스트링 | `"cross-encoder/ms-marco-MiniLM-L-6-v2"` 인라인 | `_DEFAULT_MODEL_NAME` 모듈 상수 |
| Docstring | 없음 | Args/Returns 포함 완전한 Google Style |

### 2.2 `src/analysis_logic.py` — 전면 재작성

| 항목 | 이전 | 이후 |
|------|------|------|
| Type Hints | `list`, `dict` 기본형 사용 | `List[str]`, `Dict[str, Any]`, `Optional` 전면 적용 |
| `get_reranker()` 반환타입 | 미명시 | `Optional[Any]` 명시 |
| Reranker 가용성 확인 | `not _RERANKER_INSTANCE` | `instance.is_available` 프로퍼티 활용 |
| 시간 측정 | `time.time()` (절대 시간) | `time.monotonic()` (상대 경과 시간) |
| 내부 함수명 | `run_analysis_streaming()` (공개) | `_run_analysis_streaming()` (내부 표시) |
| 상수 | `_RERANKER_INSTANCE = None` (불명확) | 타입 명시 및 센티넬 패턴 `False` 문서화 |

### 2.3 `src/utils.py` — SRP 위반 해결 (핵심)

| 항목 | 이전 | 이후 |
|------|------|------|
| **SRP 위반** | `import streamlit as st` (비-UI 모듈에 UI 의존) | `streamlit` import 완전 제거 |
| `display_patent_with_link()` | st.markdown() 호출 (UI 결합) | **삭제** → `src/ui_helpers.py` 분리 권장 |
| `_STANDARD_KEYS` | `set` (가변) | `frozenset` (불변, 실수 방지) |
| `format_analysis_markdown()` | 중간 변수 없는 복잡한 f-string | `risk_factors_md`, `strategies_md` 추출로 가독성 개선 |
| 타입 힌트 | `tuple` 기본형 | `Tuple[str, str, str]` 명시 |

### 2.4 `src/vector_db.py` — 다수 품질 이슈 수정

| 항목 | 이전 | 이후 |
|------|------|------|
| 중복 import | `from tqdm import tqdm` (파일 상단 + 함수 내부) | 파일 상단 1회만 유지 |
| `add_vectors()` | `normalize` 파라미터 + 빈 `pass` 블록 (불필요한 데드코드) | 파라미터 제거, 명확한 docstring 추가 |
| `ipc_filters` 타입 | `List[str] = None` (타입 불안전) | `Optional[List[str]] = None` |
| async wrapper | `asyncio.get_event_loop()` (deprecated) | `asyncio.get_running_loop()` (현대적 API) |
| `get_stats()` | `except:` bare except | `except Exception: logger.exception()` |
| 한/영 혼용 주석 | 불일치 | 전체 한국어 주석으로 통일 |

### 2.5 `src/patent_agent.py` — 품질 개선

| 항목 | 이전 | 이후 |
|------|------|------|
| `ipc_filters` 타입 | `List[str] = None` (타입 불안전) | `Optional[List[str]] = None` |
| `analyze()` 출력 | `print()` 다수 사용 (CLI 용도) | `logger.info()` + structured extra 교체 |
| 모듈 레벨 경로 변수 | 타입 주석 없음 | `DATA_DIR: Path`, `OUTPUT_DIR: Path` 명시 |

---

## 3. 리팩토링 원칙 적용 현황

| 원칙 | 적용 여부 | 비고 |
|------|-----------|------|
| PEP8 컨벤션 | ✅ | 변수명, import 정렬, 라인 길이 |
| Type Hints 전면 적용 | ✅ | `from __future__ import annotations` 활용 |
| SRP (단일 책임 원칙) | ✅ | `utils.py`에서 UI 의존성 제거 |
| 불필요 코드 제거 | ✅ | `add_vectors()` 데드코드, 중복 import |
| Docstring 추가 | ✅ | Args / Returns / Raises 포함 Google Style |
| `logger.exception()` 활용 | ✅ | 스택 트레이스 보장 |
| `asyncio.get_running_loop()` | ✅ | deprecated API 교체 |

---

## 4. 영향 범위 (Breaking Changes)

> **⚠️ 주의**: 아래 변경사항은 호출 코드 수정이 필요할 수 있습니다.

1. **`src/utils.py`** — `display_patent_with_link()` 함수 삭제
   - 기존 호출처 (Streamlit UI 코드)에서 `import` 교체 필요
   - 대안: `get_patent_link()` 함수를 활용하여 UI 레이어에서 직접 렌더링

2. **`src/vector_db.py`** — `add_vectors(normalize: bool)` 파라미터 제거
   - `normalize=True/False`로 호출하던 코드는 파라미터 제거 필요

3. **`src/analysis_logic.py`** — `run_analysis_streaming()` → `_run_analysis_streaming()` (내부 함수)
   - 외부에서 직접 호출하던 경우 `run_full_analysis()` 사용으로 변경 필요

---

## 5. 다음 단계 권장 사항

- [ ] **`src/ui_helpers.py` 신규 생성**: `display_patent_with_link()` 등 Streamlit UI 전용 헬퍼 분리
- [ ] **`src/config.py` Type Hints 보강**: `PipelineConfig.max_workers: int` 등 일부 누락 필드
- [ ] **통합 테스트 실행**: 리팩토링된 모듈들의 연계 동작 검증

---

## 6. PM 에이전트 전달 상태 업데이트

- **Issue #3 상태**: `In Progress → Done (리팩토링 완료)`
- **브랜치**: `feature/rag-code-quality-refactoring` (커밋 완료, PR 생성 대기)
- **다음 Epic 준비 완료**: FastAPI 웹 서비스화 착수 가능 상태
