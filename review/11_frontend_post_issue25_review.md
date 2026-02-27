### 🔍 총평 (Architecture Review)
이슈 #25의 모든 항목이 구현되었고, Rate Limit 에러 처리가 전화면 ErrorFallback에서 오버레이 모달로 올바르게 분리되었습니다. `useHistory`의 Graceful Fallback 처리와 `RateLimitModal`의 카운트다운 타이머 구조는 프로덕션 품질에 가까운 수준입니다. 다만 `App.tsx:39`의 문자열 기반 에러 판별, `App.tsx:52~64`의 논리 결함, `useHistory.ts:35`의 세션 ID URL 노출 등 수정이 필요한 항목이 남아 있습니다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Frontend 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `App.tsx:39` — **에러 타입 판별을 문자열 `.includes()`에 의존 — 깨지기 쉬운 설계**
  - 문제점: `errorInfo?.title.includes('분석 한도')` 로 에러 종류를 판별하는 것은 메시지 텍스트가 바뀌는 순간 모달이 표시되지 않는 무소음(Silent) 버그를 유발합니다.
  - 해결 방안: `useRagStream`의 `RagErrorInfo`에 `code` 필드를 추가하고 판별에 사용하세요:
    ```typescript
    // useRagStream.ts - RagErrorInfo 인터페이스 수정
    export interface RagErrorInfo {
        code: 'RATE_LIMITED' | 'SESSION_EXPIRED' | 'TOKEN_EXCEEDED' | 'NOT_FOUND' | 'TIMEOUT' | 'NETWORK_ERROR';
        title: string;
        message: string;
    }
    // App.tsx - 코드 기반으로 판별
    const isRateLimited = errorInfo?.code === 'RATE_LIMITED';
    ```

- `App.tsx:52~64` — **`handleViewHistoryResult`의 캐시 로직 결함 — `record.result`가 있어도 재분석 호출**
  - 문제점: `if (record.result)` 브랜치에서 `setIsComplete(true)` 후 즉시 `startAnalysis(record.idea)`를 추가로 호출합니다. 이는 캐시 결과를 덮어씌우는 불필요한 API 재호출을 발생시킵니다.
  - 해결 방안: 캐시 결과가 있을 때 `startAnalysis` 호출을 제거하고, `resultData`를 직접 주입하는 방식을 사용하세요. 현재 구조에서는 `useRagStream`에 `setResultData`를 노출하거나, 별도의 `loadCachedResult(result)` 함수를 추가하는 것을 권장합니다.

- `useHistory.ts:35` — **세션 ID가 URL 쿼리 파라미터로 노출**
  - 문제점: `?session_id=${sessionId}`를 URL에 포함하면 브라우저 히스토리, 서버 액세스 로그, Nginx 로그에 세션 식별자가 평문으로 기록됩니다. 보안 모범 사례에 어긋납니다.
  - 해결 방안: 이미 `X-Session-ID` 헤더를 전송하고 있으므로, URL 쿼리 파라미터를 제거하고 헤더만 사용하도록 백엔드와 협의하세요:
    ```typescript
    // URL에서 session_id 제거
    const response = await fetch(`${apiUrl}/api/history`, {
        headers: { 'X-Session-ID': sessionId }
    });
    ```

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `RateLimitModal.tsx:1` — **`useCallback` 임포트되었으나 미사용**
  - 불필요한 임포트입니다. `import { useEffect, useRef, useState } from 'react'`로 수정하세요.

- `RateLimitModal.tsx:17` — **`retryAfter` prop 변경 시 카운트다운이 재시작되지 않음**
  - `useEffect` 의존성 배열이 `[]`이므로, 부모가 `retryAfter` 값을 변경해도 타이머가 초기화되지 않습니다. 현재 구조상 모달이 새로 마운트될 때마다 초기화되므로 실용적으로는 문제없으나, `retryAfter` prop을 의존성으로 추가하는 것이 명시적입니다.

- `App.tsx:52` — **`handleViewHistoryResult`의 `useCallback` 의존성 배열이 비어있음**
  - `setIsComplete`, `setErrorInfo`, `startAnalysis`, `handleSubmit`을 내부에서 사용하지만 의존성 배열이 `[]`입니다. ESLint `exhaustive-deps` 경고가 발생하며 stale closure 위험이 있습니다.

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `useHistory.ts:55~59` — **에러 발생 시 무소음 처리 — 향후 디버깅 어려움**
  - 현재 `catch` 블록에서 에러를 완전히 무시합니다. 개발 환경에서만이라도 사용자에게 표시하거나, `setError`를 활성화할 조건(`process.env.NODE_ENV === 'development'`)을 추가하세요.

- `App.tsx:67` — **`handleRerun`의 `handleSubmit` 의존성 누락**
  - `handleSubmit`을 `useCallback`으로 래핑하지 않아 `handleRerun`이 매 렌더마다 새 함수 참조를 받습니다. `handleSubmit`도 `useCallback`으로 감싸는 것을 권장합니다.

---

### 📊 #25 이슈 최종 구현 현황

| 항목 | 상태 |
|---|---|
| `RateLimitModal.tsx` 전용 모달 | ✅ 구현 완료 |
| 카운트다운 타이머 | ✅ 구현 완료 |
| `HistorySidebar.tsx` 사이드바 | ✅ 구현 완료 |
| `HistoryItem`, `HistoryEmpty` | ✅ 구현 완료 |
| `useHistory.ts` 페치 훅 | ✅ 구현 완료 |
| `HistoryRecord` 타입 | ✅ 구현 완료 |
| 에러 코드 기반 판별 | ❌ 미적용 (Critical) |
| 히스토리 캐시 결과 보기 | ⚠️ 로직 결함 (Critical) |
| 세션 ID URL 노출 | ❌ 보안 이슈 (Critical) |

---

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 3건(에러 코드 기반 판별, 캐시 결과 보기 로직 결함, 세션 ID URL 노출)을 수정한 후 머지를 권장합니다. Warning 항목은 다음 PR에서 처리해도 무방합니다.**
