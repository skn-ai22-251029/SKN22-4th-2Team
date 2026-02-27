### 🛠️ 프론트엔드 코드베이스 분석 결과
(현재 UI 코드의 문제점 및 반응성/접근성 개선 방향 요약)

기존 파이썬(Streamlit) 코드베이스에 통합되어 있던 프론트엔드 로직의 결합도를 낮추고 사용자 반응성을 극대화하기 위해 독립적인 형태의 **React 18 SPA(Single Page Application)** 환경으로 구축을 시작했습니다.

- **성과:** TypeScript 및 Tailwind CSS 기반의 `frontend` 폴더 뼈대가 세팅되었습니다.
- **개선 컴포넌트 (`ProgressStepper.tsx`, `RagSkeleton.tsx`):** 기존 `app.py` 동작 시 타임아웃 오류 및 무한 로딩 대비책으로 기획되었던 **'단계별 스텝퍼'**, **'시간 지연 토스트(30초 초과 시)'**, **'동적 스켈레톤 애니메이션'** 컴포넌트를 React 기반으로 온전히 분리 구현했습니다.
- **문제점 및 차후 과제:** 현재 `App.tsx`는 백엔드 스트리밍 통신 없이 클라이언트 안에서만 `setInterval`을 이용해 가상의 시뮬레이션으로 동작하고 있습니다. 향후 백엔드 RAG API(FastAPI 등)와 실제 SSE 연동이 필수적입니다.

---

### 📋 PM 및 Backend 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: UI 컴포넌트 고도화 (Frontend)**
  - [x] RAG 전용 로딩 스켈레톤(Skeleton UI) 추가 완료 (`RagSkeleton.tsx`)
  - [x] 진행률, 타임아웃 알림 기능을 갖춘 다이내믹 스텝퍼 추가 완료 (`ProgressStepper.tsx`)
  - [ ] 검색창 및 결과 시각화 컴포넌트 상세 분리 (추후 진행)
- **Epic: 백엔드 API 통신 연동 (Frontend)**
  - [ ] App.tsx 내 가상 시뮬레이션을 대체할 특허 검증 엔드포인트 비동기(SSE) 통신 로직 작성 (진행 대기)
- **Epic: 백엔드 협업 요청 (Backend에게 전달할 사항)**
  - [ ] FastAPI 기반의 완전한 비동기 SSE 스트리밍 라우터 신규 구축 요청
  - [ ] 에러 발생 시 명확한 HTTP Status Code(429, 504 등) 및 안내 메시지 포맷 지정 요청
