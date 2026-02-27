# 15. 클라이언트 세션 ID 생성 및 서버 연동 설계

클라이언트를 고유하게 식별하는 세션 ID를 생성하여 모든 API 요청에 포함시키고, 서버의 Rate Limit 및 히스토리 조회 기능을 안정적으로 연동합니다.

---

## 🎯 1. 세션 ID 생성 전략

### 사용 기술: UUID v4 (외부 라이브러리 없이 브라우저 내장 API 활용)
- 별도 패키지 설치 없이 브라우저 내장 `crypto.randomUUID()` API를 사용합니다.
- 지원 환경: Chrome 92+, Firefox 95+, Safari 15.4+ (모던 브라우저 전부 지원)

```typescript
// UUID v4 생성 예시 (crypto.randomUUID 사용)
const newSessionId = crypto.randomUUID(); // e.g. "110e8400-e29b-41d4-a716-446655440000"
```

### 저장 위치 결정: `localStorage` 우선, Cookie 보완
| 저장소 | 장점 | 단점 |
|---|---|---|
| `localStorage` | 간단, 영구 저장, JavaScript 접근 용이 | 탭/도메인 공유, 시크릿 모드 초기화 |
| `sessionStorage` | 탭 격리 | 탭 닫으면 삭제 |
| `Cookie` | 서버 자동 전송, 유효 기간 설정 | CORS/SameSite 정책 복잡 |

✅ **선택**: `localStorage` 기반으로 저장하되, 시크릿 모드 대응을 위해 저장 실패 시 메모리(`in-memory`) 변수로 폴백합니다.

---

## 🛠️ 2. 구현 설계

### A. `useSessionId` 훅 신규 생성

**파일 경로**: `frontend/src/hooks/useSessionId.ts`

```typescript
// 훅 동작 순서:
// 1. localStorage에서 'shortcut_session_id' 키로 기존 ID 조회
// 2. 없으면 crypto.randomUUID()로 신규 생성 후 저장
// 3. localStorage 접근 실패(시크릿 모드 등) 시 메모리 변수에 저장
// 4. 생성된 sessionId를 반환
```

**시크릿 모드 폴백 로직**:
```typescript
const getOrCreateSessionId = (): string => {
    const KEY = 'shortcut_session_id';
    try {
        const existing = localStorage.getItem(KEY);
        if (existing) return existing;
        const newId = crypto.randomUUID();
        localStorage.setItem(KEY, newId);
        return newId;
    } catch {
        // localStorage 블락(시크릿 모드, 권한 없음 등)
        return crypto.randomUUID(); // 메모리 일회성 발급
    }
};
```

### B. `useRagStream` 훅에 X-Session-ID 헤더 자동 포함

**파일 경로**: `frontend/src/hooks/useRagStream.ts` (수정)

```typescript
// fetch 호출부에 헤더 추가
const response = await fetch(`${apiUrl}/api/analyze`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'X-Session-ID': sessionId,  // ← 추가
    },
    body: JSON.stringify({ idea }),
    signal: abortController.signal,
});
```

### C. 세션 ID 재발급 로직

서버가 `401 Unauthorized` 또는 특정 에러 응답으로 세션 무효화를 알려줄 경우:
1. `localStorage`의 기존 세션 ID를 삭제
2. `crypto.randomUUID()`로 신규 ID 재생성 후 저장
3. 자동으로 재요청(retry) 수행

---

## 🌐 3. 다중 탭 및 시크릿 모드 대응

| 시나리오 | 동작 | 비고 |
|---|---|---|
| 일반 탭 재방문 | `localStorage` 동일 ID 유지 ✅ | 히스토리 조회 가능 |
| 다중 탭 동시 사용 | 동일 `localStorage` → 동일 ID 공유 ✅ | 동일 사용자로 식별됨 |
| 시크릿 모드 | `localStorage` 차단 → 메모리 one-time ID 발급 ⚠️ | 세션 유지 불가 (브라우저 설계 제한) |
| 탭 닫고 재시작 | `localStorage` 동일 ID 유지 ✅ | |

> ⚠️ **시크릿 모드**: 브라우저 정책상 `localStorage`가 차단되므로 세션 ID를 영구 저장할 수 없습니다. 이는 기술적 제한 사항으로, 시크릿 탭에서는 매 방문마다 새 사용자로 인식됩니다. 서버에 이를 명시합니다.

---

## 📋 PM 및 Backend 전달용 피드백

- **Epic: 세션 ID 연동 (Frontend)**
  - [ ] `useSessionId.ts` 훅 신규 구현 (UUID v4 생성, localStorage 저장/폴백)
  - [ ] `useRagStream.ts` 수정 — 모든 fetch 요청에 `X-Session-ID` 헤더 포함

- **Epic: 백엔드 협업 요청 (Backend에게 전달할 사항)**
  - [ ] `/api/analyze` 엔드포인트에서 `X-Session-ID` 헤더를 읽어 요청자 식별 처리 요청
  - [ ] Rate Limit 검증 시 `X-Session-ID` 기반 카운팅 적용 확인 요청
  - [ ] 세션 ID가 누락되거나 무효화된 경우 별도 HTTP 상태 코드 정의 요청 (예: `401` 또는 `X-Session-Expired` 헤더)
