### 🔍 총평 (Architecture Review)

프론트엔드의 React/Vite 기반 전환 및 SSE 실시간 스트리밍 구현은 매우 훌륭합니다. 하지만 **하드코딩된 API 엔드포인트** 및 **네트워크 타임아웃 미비점**은 컨테이너 기반(도커/AWS) 프로덕션 환경으로 나아가기 위해 반드시 수정되어야 하는 치명적 취약점입니다.

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `src/hooks/useRagStream.ts:33` - **API URL 하드코딩:** `http://localhost:8000` 주소가 코드에 강하게 결합되어 있습니다. Docker-compose 구동 및 AWS 배포 시 서버 주소가 동적으로 변하므로, `fetch(import.meta.env.VITE_API_URL + '/api/analyze')` 와 같이 환경 변수(`VITE_`) 기반으로 즉시 분리해야 합니다.
- `src/hooks/useRagStream.ts:15` - **스트림 타임아웃(Timeout) 부재:** `TimeoutToast`로 30초 지연 UI 경고는 띄우고 있으나, 실제 `fetch` 요청을 강제 종료하는 백그라운드 타이머가 없습니다. 서버 장애 리소스 낭비를 막기 위해 `setTimeout`과 `abortController.abort()`를 결합하여 절대 타임아웃(예: 60초)을 강제해야 합니다.

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `src/components/Form/IdeaInput.tsx:13` - **Prompt Injection 취약점:** 사용자 입력(`idea`)에 대한 검증이 단순 길이(10자) 체크만 있습니다. 악의적인 프롬프트 인젝션 문자열 우회(`\n\nIgnore previous instructions...`)나 스크립트 실행 방지를 위해 기본적인 클라이언트 사이드 새니타이징(Sanitization) 혹은 정규식 필터링 도입을 고려해 주세요.
- `src/hooks/useRagStream.ts:117` - **에러 핸들링 UX 저하:** 에러 발생 시 브라우저 기본 `alert()` 창을 띄우고 있습니다. 브라우저 스레드를 강제로 블로킹하므로, React 전역 에러 토스트(Global Error Boundary)로 교체하는 것이 유지보수와 사용성에 좋습니다.

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `src/utils/exportPdf.ts` (또는 해당 컴포넌트) - PDF 생성용 `html2canvas`와 `jspdf` 라이브러리는 파일 용량이 매우 무겁습니다. 사용자가 "다운로드 버튼"을 눌렀을 때만 로드되도록 동적 임포트(`const html2canvas = (await import('html2canvas')).default;`)를 적용하면 앱의 초기 JS 번들 및 TTI(Time To Interactive) 속도가 획기적으로 향상될 것입니다.

### 💡 Tech Lead의 머지(Merge) 권고

- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [X] Critical 항목이 수정되기 전까지 머지를 보류하세요.
