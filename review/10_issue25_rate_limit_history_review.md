### 🔍 총평 (Architecture Review)
이슈 #25의 두 가지 핵심 기능(Rate Limit 전용 모달, 검색 히스토리 사이드바)은 **현재 코드베이스에 구현되어 있지 않습니다.** `useRagStream.ts`에 `RATE_LIMITED` 에러 메시지 처리(429 분기)가 추가된 것은 확인되나, 이는 기존 `ErrorFallback` 컴포넌트를 통한 텍스트 안내일 뿐 전용 모달 UI가 아닙니다. 기획서(`17번 문서`)는 완성되어 있으나 실제 컴포넌트 구현이 선행되어야 합니다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Frontend 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- **`components/common/RateLimitModal.tsx` 파일 없음** — **429 전용 모달 UI 미구현**
  - 문제점: `useRagStream.ts`에서 `status === 429`를 `RATE_LIMITED` 에러로 분기하는 로직은 존재하지만, `App.tsx`에서 이를 `ErrorFallback` 컴포넌트로 처리하고 있습니다. `ErrorFallback`은 일반 에러용 전체 화면 UI이며, 17번 설계 문서에서 기획한 **오버레이 모달 + 카운트다운 타이머 + 히스토리 이동 버튼**이 전혀 구현되어 있지 않습니다.
  - 해결 방안: 기획서(`17_rate_limit_history_sidebar_design.md`) 기준으로 다음 파일을 생성해야 합니다:
    ```
    components/common/RateLimitModal.tsx
    ```
    - 기능: `errorInfo.title === '분석 한도에 도달했습니다...'` 조건으로 오버레이 표시, `Retry-After` 응답 헤더 기반 카운트다운 타이머, "히스토리 보기" CTA

- **`components/History/` 디렉토리 없음** — **검색 히스토리 사이드바 전혀 미구현**
  - 문제점: 다음 파일들이 모두 존재하지 않습니다:
    ```
    components/History/HistorySidebar.tsx   ← 사이드바 컨테이너
    components/History/HistoryItem.tsx      ← 히스토리 카드
    components/History/HistoryEmpty.tsx     ← 빈 상태 플레이스홀더
    hooks/useHistory.ts                     ← 히스토리 데이터 페치 훅
    ```
  - 해결 방안: `17번 기획서`의 세션 기반 `GET /api/history?session_id={}` 연동 포함하여 구현 필요

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `App.tsx:47~66` — **RATE_LIMITED 에러가 ErrorFallback을 통해 전체 화면으로 표시됨**
  - 문제점: 현재 429 에러 발생 시 화면 전체가 에러 폴백으로 전환되어, 사용자가 다시 분석을 시작하려면 "새 아이디어로 돌아가기"를 눌러야 합니다. Rate Limit 상황에서는 오버레이 모달로 안내하여 **뒤 화면(입력창)은 유지**하는 것이 올바른 UX입니다.
  - 개선 방안: `App.tsx`에 `isRateLimited` 상태를 분리하고, `RATE_LIMITED` 에러는 `RateLimitModal`로 따로 처리하세요.

- `types/rag.ts` — **히스토리 레코드 타입 정의 없음**
  - `useHistory.ts` 구현 시 필요한 `HistoryRecord` 타입이 없습니다:
    ```typescript
    export interface HistoryRecord {
        id: string;
        idea: string;
        riskLevel: 'Low' | 'Medium' | 'High';
        riskScore: number;
        similarCount: number;
        createdAt: string;
    }
    ```

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `App.tsx` — **헤더 영역에 "📋 히스토리" 토글 버튼 추가 필요**
  - 현재 `App.tsx`에는 헤더나 내비게이션이 없습니다. 히스토리 사이드바와 세션 ID 정보를 노출할 글로벌 헤더 컴포넌트(`Header.tsx`)를 추가하면 UX가 크게 향상됩니다.

---

### 📋 현재 이슈 #25 구현 현황 체크리스트

| 항목 | 상태 |
|---|---|
| `useRagStream.ts` 429 에러 분기 | ✅ 완료 |
| `RATE_LIMITED` 에러 메시지 정의 | ✅ 완료 |
| `RateLimitModal.tsx` 전용 모달 UI | ❌ 미구현 |
| 카운트다운 타이머 (`Retry-After`) | ❌ 미구현 |
| `HistorySidebar.tsx` 사이드바 컨테이너 | ❌ 미구현 |
| `HistoryItem.tsx` 히스토리 카드 | ❌ 미구현 |
| `HistoryEmpty.tsx` 빈 상태 UI | ❌ 미구현 |
| `useHistory.ts` 데이터 페치 훅 | ❌ 미구현 |
| `types/rag.ts` HistoryRecord 타입 | ❌ 미구현 |

---

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 항목(RateLimitModal, HistorySidebar 미구현)이 완성되기 전까지 이슈 #25는 Done 처리 불가입니다. Frontend 에이전트에게 구현을 즉시 요청하세요.**
