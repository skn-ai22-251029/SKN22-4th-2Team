### 🛠️ 프론트엔드 코드베이스 분석 및 리팩토링 결과
(현재 UI 코드의 문제점 및 반응성/접근성 개선 방향 요약)

시니어 리뷰어(Chief Architect)의 피드백을 수용하여 `App.tsx` 내에 존재하던 치명적인 메모리 누수 버그 및 하드코딩된 비즈니스 로직 결합 문제를 전면 리팩토링했습니다. 아울러 아이디어 검색창 및 결과 시각화 컴포넌트를 용도에 맞게 완벽히 분리했습니다.

- **성과 1 (메모리 누수 해결):** 가상의 타이머(interval) ID를 `useRef`로 관리하는 커스텀 훅 `useRagStream.ts`를 도입하여, 작동 도중 '정지'를 누르거나 컴포넌트가 언마운트되어도 즉시 `clearInterval`이 실행되도록 좀비 프로세스를 차단했습니다.
- **성과 2 (관심사 분리):** 무거웠던 `App.tsx` 코드 100줄 분량을 걷어내고, `<IdeaInput>`(입력), `<ProgressStepper>`(로딩), `<ResultView>`(결과 렌더링) 이라는 선언형(Declarative) 컴포넌트로 깔끔하게 조립(Composition)했습니다.
- **향후 확장성(Scale-up):** 이제 `useRagStream` 훅 내부의 로직만 실제 백엔드 API(FastAPI SSE) 통신 코드로 1:1 교체하면 UI의 수정 없이 완벽하게 실제 애플리케이션으로 작동시킬 수 있습니다.

---

### 📋 PM 및 Backend 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: UI 컴포넌트 고도화 (Frontend)**
  - [x] App.tsx 메모리 누수 치명적 결함 수정 및 커스텀 훅(`useRagStream`) 분리 완료
  - [x] 사용자 최적화 텍스트 에어리어가 적용된 검색창 분리 (`IdeaInput.tsx`) 완료
  - [x] RAG 요약 정보(위험도, 유사도) 및 마크다운 시각화를 위한 결과창 분리 (`ResultView.tsx`) 완료
  - [ ] **(New)** 결과창 다운로드 버튼 클릭 시 `html2canvas` 등을 이용한 PDF 내보내기 기능 추가 (추후 기획 확정 시)

- **Epic: 백엔드 API 통신 연동 (Frontend)**
  - [ ] 프론트엔드 UI 화면 뼈대 완성이 모두 종료되었으므로, **"실제 FastAPI 백엔드 연동 통신 로직(`axios` 및 `EventSource`)"** 작성 단계 진입 준비

- **Epic: 백엔드 협업 요청 (Backend에게 전달할 사항)**
  - [ ] 프론트엔드 개발자가 API를 바로 연결할 수 있도록, FastAPI 기반의 **`POST /api/analyze` (비동기 SSE 스트리밍 방식)** 엔드포인트 명세서(Swagger 또는 마크다운)를 신속히 공유해 주기 바랍니다.
