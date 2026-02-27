# 19. #25 Rate Limit UI & 검색 히스토리 사이드바 구현 완료 보고

## ✅ 작업 요약
10번 리뷰(issue #25 미구현 지적) 피드백을 기반으로 신규 파일 5개를 생성하고, `types/rag.ts`와 `App.tsx`를 업데이트했습니다.

---

## 🔄 변경 내역

### 신규 생성 파일

| 파일 | 설명 |
|---|---|
| `components/common/RateLimitModal.tsx` | 429 전용 오버레이 모달 (카운트다운 타이머, 히스토리 이동 CTA) |
| `components/History/HistoryItems.tsx` | `HistoryEmpty` (빈 Placeholder) + `HistoryItem` (카드) 통합 |
| `components/History/HistorySidebar.tsx` | 슬라이드인/아웃 사이드바 컨테이너 (로딩 스켈레톤 포함) |
| `hooks/useHistory.ts` | `GET /api/history?session_id={}` 데이터 페치 훅 |

### 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `types/rag.ts` | `HistoryRecord` 인터페이스 추가 |
| `App.tsx` | RateLimitModal 오버레이, HistorySidebar 토글, 글로벌 헤더, RATE_LIMITED 분리 처리 |

---

## 🎨 UI/UX 개발 내용 요약

- **RateLimitModal**: 429 발생 시 배경(입력창)을 유지한 채 오버레이만 표시. `Retry-After` 헤더 기반 카운트다운 타이머 지원. "검색 히스토리 보기" CTA로 사이드바 연결.
- **HistorySidebar**: 헤더 우측 "📋 히스토리" 버튼으로 토글. 세션 ID 기반 `GET /api/history` 호출. 위험도 뱃지·날짜·요약·버튼을 포함한 카드 UI. 데이터 없으면 `HistoryEmpty` 표시.
- **글로벌 헤더**: `fixed` 상단 헤더에 "✂️ Short-Cut" 로고와 히스토리 토글 버튼 배치.

---

## 📋 Backend에게 전달할 협업 요청 사항

- **`GET /api/history?session_id={id}`** 신규 엔드포인트 개발 요청
  ```json
  [
    {
      "id": "string",
      "idea": "string (50자 요약)",
      "riskLevel": "High | Medium | Low",
      "riskScore": 85,
      "similarCount": 4,
      "createdAt": "2026-02-27T17:00:00Z"
    }
  ]
  ```
- **429 응답 `Retry-After` 헤더** 포함 요청 (초 단위, 카운트다운 타이머용)
- **현재 `useHistory.ts`는 백엔드 미연동 상태에서 빈 배열을 반환**하도록 Graceful Fallback이 적용되어 있습니다.
