### 🔍 총평 (Architecture Review)
FastAPI 앱 초기화 단계에서 시크릿 로딩 시점을 끌어올려 API 500 오류를 해결하고 Rate Limiter 예외 처리를 복원한 것은 적절한 긴급 조치입니다. 하지만 모듈 레벨에서 환경 변수를 캐싱하는 파이썬 안티패턴(Anti-pattern)이 그대로 남아 있어, 향후 임포트 순서가 바뀌거나 테스트 코드를 작성할 때 동일한 버그가 재발할 구조적 위험이 존재합니다.

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Backend 또는 DevOps 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**
- `src/patent_agent.py:53~73` 등 - **환경변수 모듈 레벨 하드캐싱 방지**
  - **문제점 설명:** `OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")`를 비롯한 각종 환경변수들이 모듈 최상단에서 한 번만 평가되어 고정되고 있습니다. 이는 앱의 생명주기가 `main.py`의 `bootstrap_secrets()` 실행 시점과 타 모듈의 로드 순서에 극도로 의존하게 만들어, 사소한 임포트 변경에도 API 키 부재 오류를 뱉기 쉽습니다.
  - **해결 코드 제안:** 예로 들어 모듈 레벨의 `os.environ.get()` 할당을 삭제하고, `PatentAgent` 스코프 내부나 팩토리/`__init__()` 단계에서 동적으로 참조하도록 리팩토링하세요. 또한 `src.config`와 설정 진입점을 한 곳으로 통합하는 것이 좋습니다.

**[🟡 Warning: 잠재적 위험 - 개선 권장]**
- `src/api/main.py:11-14` - **시크릿 로딩 실패 시 Fast-fail 부재**
  - **성능/보안 위험 설명:** 프로덕션 빌드에서 AWS Secrets Manager 인증 실패 혹은 타임아웃으로 시크릿 로드에 실패하면, `warning` 로그만 출력한 뒤 빈 문자열 상태로 서버가 열려버립니다. 이후 런타임에 유저가 접근하면 예상치 못한 예외 및 500 응답이 발생하므로, 애플리케이션 컨테이너 자체를 중단(Fast-fail)시켜 ALB 헬스체크를 통과하지 못하게 막는 것이 안전합니다.

**[🟢 Info: 클린 코드 및 유지보수 제안]**
- 설정의 **Single Source of Truth(단일 진입점)** 적용: 현재 `config.py`, `patent_agent.py`, `dependencies.py` 곳곳에서 `load_dotenv()` 와 `os.environ`이 개별적으로 호출되는 파편화 현상이 관찰됩니다. 모든 앱 설정은 `src.config.py`의 `config` 인스턴스로 일원화하여 참조하는 구조로 향상시키길 권장합니다.

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] Critical 항목이 수정되기 전까지 머지를 보류하세요.
