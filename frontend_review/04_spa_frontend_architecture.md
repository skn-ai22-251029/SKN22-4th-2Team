# 🚀 Frontend Architecture & Folder Structure (SPA)

현재 `app.py`(Streamlit) 기반으로 동작 중인 쇼특허(Short-Cut) 서비스의 프론트엔드를 완전한 **React(Next.js 권장) 기반의 SPA(Single Page Application) 아키텍처**로 분리 구축하기 위한 폴더 구조 및 기술 명세입니다.

이 구조는 앞서 도출된 RAG 로딩 UI(SSE 스트리밍, 스텝퍼), 복잡한 상태 관리(History, 폼 유효성 검사)를 안정적으로 처리하기 위해 설계되었습니다.

---

## 🏗️ 1. 기술 스택 (Tech Stack) 제안
- **Core:** React 18+ / Next.js (App Router 권장 - SEO 및 초기 로딩 최적화)
- **Language:** TypeScript (안정적인 데이터 타이핑 및 API 응답 인터페이스 관리)
- **Styling:** Tailwind CSS + Shadcn UI (또는 Styled-Components) - 스켈레톤 및 프로그레스바의 빠른 구현
- **State Management:** Zustand (전역 유저 상태 및 히스토리 관리)
- **Data Fetching:** TanStack Query (React Query) + Server-Sent Events(SSE) 기본 브라우저 API (EventSource)

---

## 📁 2. 프론트엔드 전체 폴더 구조안 (`/frontend` 디렉토리 하위)

```text
frontend/
├── public/                 # 정적 리소스 (이미지, 폰트, 로고, 가이드 PDF 등)
├── src/
│   ├── app/                # Next.js App Router 기반 라우팅 (페이지)
│   │   ├── page.tsx        # 메인 페이지 (아이디어 입력 폼)
│   │   ├── result/         # 분석 결과 페이지 (침해 리스크, 유사도 표출)
│   │   ├── history/        # 사용자 과거 검색 내역 페이지
│   │   └── layout.tsx      # 글로벌 레이아웃 (Header, Sidebar, Footer)
│   │
│   ├── components/         # 재사용 가능한 UI 컴포넌트
│   │   ├── common/         # 공통 컴포넌트 (Button, Input, Modal, Badge)
│   │   ├── layout/         # 레이아웃 전용 컴포넌트 (Sidebar.tsx, Header.tsx)
│   │   ├── Loading/        # RAG 전용 로딩 UI (★★ 핵심)
│   │   │   ├── RagSkeleton.tsx  # 스트리밍 대기 중 보여줄 스켈레톤 뼈대
│   │   │   ├── ProgressStepper.tsx # 검색중->분석중->생성중 단계별 프로그레스
│   │   │   └── TimeoutToast.tsx # 30초 초과 지연 안내 토스트
│   │   └── form/           # 입력 폼 관련 (IdeaInput.tsx, CategorySelect.tsx)
│   │
│   ├── hooks/              # 커스텀 리액트 훅
│   │   ├── useRagStream.ts # [SSE] RAG 스트리밍 통신 및 상태 파싱 전용 훅
│   │   ├── useIdeaValidation.ts # 폼 유효성 검사 로직
│   │   └── useHistory.ts   # 조회 기록 로컬/서버 연동 훅
│   │
│   ├── services/           # 백엔드 API 통신 레이어 (Axios / Fetch)
│   │   ├── api.ts          # 기본 Axios 인스턴스 (인터셉터, 에러 핸들링 포함)
│   │   ├── patent.ts       # 특허 조회 및 분석 관련 엔드포인트
│   │   └── auth.ts         # (향후 대비) 사용자 인증 로직
│   │
│   ├── store/              # 전역 상태 관리 (Zustand)
│   │   └── useAppStore.ts  # 검색 중 상태, 결과 데이터 임시 저장소
│   │
│   ├── types/              # TypeScript 인터페이스 및 타입 정의
│   │   ├── api.d.ts        # RAG SSE 응답 객체 타입 정의 (percent, step_info 등)
│   │   └── patent.d.ts     # 유사도 점수, 침해 리스크 데이터 모델
│   │
│   └── utils/              # 헬퍼 함수
│       ├── formatters.ts   # 날짜, 마크다운 변환 헬퍼
│       └── colorMap.ts     # 리스크 등급별 색상 매핑 함수
│
├── package.json
├── tailwind.config.js      # 스타일링 설정 가이드
├── tsconfig.json
└── .env.local              # 프론트엔드 환경변수 (NEXT_PUBLIC_API_URL 등)
```

---

## 🎯 3. 주요 구현 포인트 (기획 요구사항 연계)

1. **`hooks/useRagStream.ts` (SSE 양방향 통신)**
   - 기존 Streamlit의 `async for` 제너레이터를 대신하여, 브라우저의 `EventSource` 또는 `fetch` 스트림 리더를 통해 FastAPI의 SSE 스트림을 수신합니다.
   - `percent`(진행률), `message`(상태 문구), `stream_token`(결과 마크다운 텍스트)을 파싱하여 React의 상태(State)로 즉시 업데이트합니다.

2. **`components/Loading/ProgressStepper.tsx` (기획 문서 Epic 1)**
   - 전달받은 `percent` 값에 맞춰 1단계(검색) -> 2단계(분석) -> 3단계(결과 생성) UI의 활성화 색상을 실시간 변환시킵니다.
   - 컴포넌트 마운트 시 자체 `setInterval` 기반 타이머를 돌려 30초 경과 시 `TimeoutToast`를 호출하는 로직을 결합합니다.

3. **`services/api.ts` 중심의 에러 헨들러 (기획 문서 Epic 3)**
   - Axios Interceptor 등을 활용해 백엔드에서 429(Rate Limit), 504(Gateway Timeout)가 반환될 경우, 전역 에러 모달(Zustand 상태 트리거)을 띄우는 책임을 중앙 집중화합니다.
