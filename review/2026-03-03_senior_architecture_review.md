# Senior Architecture Review: Build & Connectivity Fixes

## 🔍 총평 (Architecture Review)

이번 패치는 빌드 중단(TypeScript 타입 불일치)과 운영 환경의 통신 단절(CORS 및 동적 ALB 주소 대응) 문제를 정확한 지점에서 해결했습니다. 특히 SSE 통신에서의 에러 파싱 로직 보강과 백엔드 전역 예외 처리기의 CORS 헤더 수동 주입은 장애 추적성을 크게 높이는 좋은 접근입니다.

## 🚨 코드 리뷰 피드백

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `infra/ecs/task-definition-template.json:28` - `ALLOWED_ORIGINS`가 `*`로 설정되어 있습니다. 현재와 같이 ALB 주소가 유동적인 초기 단계에서는 불가피한 선택이나, 도메인이 확정된 후에는 반드시 특정 도메인으로 제한하여 보안(Cross-Site Request Forgery 방어 등)을 강화해야 합니다.

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `frontend/src/hooks/useRagStream.ts:57` - `VITE_API_BASE_URL`이 없을 때 빈 문자열로 폴백하여 상대 경로를 사용하는 방식은 컨테이너 기반 배포에서 매우 권장되는 패턴입니다. 주소 하드코딩 부채를 성공적으로 제거했습니다.
- `src/api/main.py:193-199` - 미들웨어가 닿지 않는 500 에러 상황을 대비해 `global_exception_handler`에서 직접 CORS 헤더를 제어한 것은 방어적 프로그래밍 관점에서 우수합니다.

## 💡 Tech Lead의 머지(Merge) 권고

- [x] 이대로 Main 브랜치에 머지해도 좋습니다.
- [ ] Critical 항목이 수정되기 전까지 머지를 보류하세요.

> [!NOTE]
> 빌드 및 통신 이슈가 해결되었으므로, 이후 단계에서는 RAG 추론 과정의 타임아웃 발생 여부에 대한 모니터링을 강화할 것을 권장합니다.
