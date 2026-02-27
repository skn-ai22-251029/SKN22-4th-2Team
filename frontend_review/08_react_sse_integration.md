### 🛠️ 프론트엔드 코드베이스 분석 결과 및 리뷰 (SSE 백엔드 연동)
(현재 UI 코드의 문제점 및 반응성/접근성 개선 방향 요약)

기존 파이썬(Streamlit)을 대신할 React SPA 아키텍처의 프론트엔드 작업이 **완전히 마무리되었습니다.** 
가상(Mock) 데이터와 단순 타이머(`setInterval`)로 작동하던 `useRagStream` 로직을 폐기하고, 브라우저 표준인 `fetch` + `ReadableStream` 조합을 활용하여 백엔드(FastAPI)의 SSE(Server-Sent Events) 스트림을 실시간 파싱(TextDecoder)하도록 성공적으로 교체했습니다.

- **성과 1 (실시간 양방향 스트리밍 완비):** 사용자가 검색어(Idea)를 입력하면 `POST` 방식으로 백엔드에 요청을 보내고, 백엔드가 반환하는 `event: progress`, `event: complete` 텍스트 청크(Chunk)들을 실시간으로 파싱하여 스텝퍼 및 로딩 안내문(`message`)을 DOM에 그립니다.
- **성과 2 (데이터 모델링 및 타입결합):** `src/types/rag.ts`에 프론트엔드-백엔드 간 통신 규격이 될 `RagAnalysisResult`, `PatentContext` 인터페이스를 명확히 설계하고, 이를 `<ResultView />` 컴포넌트의 Props로 강력하게 바인딩하여 타입 안정성(TS 빌드 통과)을 확보했습니다.

---

### 📋 PM 및 Backend 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: UI 컴포넌트 고도화 (Frontend)**
  - [x] 검색창 및 결과 시각화 컴포넌트 분리 (`IdeaInput.tsx`, `ResultView.tsx` 분리 및 App.tsx 조립 완료)
  - [x] 로딩 스켈레톤(Skeleton UI) 추가 완료
  - [x] (New) 백엔드 규격에 맞춘 인터페이스(`interface`) 모델링 갱신 및 결과창 동적 렌더링 적용 완료

- **Epic: 백엔드 API 통신 연동 (Frontend)**
  - [x] 특허 검증 엔드포인트 비동기 통신 로직 작성 (SSE 스트림 파싱 구조 `useRagStream.ts` 적용 완료)

- **Epic: 백엔드 협업 요청 (Backend에게 전달할 사항 - 🚨🚨🚨중요🚨🚨🚨)**
  - [ ] **[긴급/핵심] API 엔드포인트 개발 요청:** 프론트엔드의 `useRagStream.ts`는 현재 백엔드 서버의 `http://localhost:8000/api/analyze` (POST) 주소로 요청을 보냅니다. 백엔드 팀은 해당 라우터를 열어주어야 합니다.
  - [ ] **[긴급/핵심] SSE 스트림 반환 포맷 준수 요청:** 백엔드는 텍스트 스트리밍 반환 시 다음과 같은 `event:` 와 `data:` 문자열 컨벤션을 지켜주어야 프론트엔드 애니메이션이 작동합니다.
    - 진행 중일 때: `event: progress\ndata: {"percent": 40, "message": "특허 문헌 파싱 중..."}\n\n`
    - 완료 시점(에러 없을 때): `event: complete\ndata: {"result": { "riskLevel": "High", "riskScore": 85, "similarCount": 3, "uniqueness": "Low", "topPatents": [ { "id": "KR-...", "similarity": 90, "title": "...", "summary": "..." } ] } }\n\n`
    - 에러 발생 시: `event: error\ndata: {"detail": "LLM API Key가 유효하지 않습니다."}\n\n`
  - [ ] 에러 발생 시 명확한 HTTP Status Code 및 안내 메시지 포맷 지정이 필요합니다.
