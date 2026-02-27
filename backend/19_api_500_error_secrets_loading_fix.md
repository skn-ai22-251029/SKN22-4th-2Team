### 🛠️ 코드베이스 분석 결과 (500 Internal Server Error 원인 파악 및 해결)

#### 1. 문제 원인
최근 발생한 간헐적인 또는 지속적인 API 500 Internal Server Error (주로 `/api/v1/analyze` 엔드포인트 호출 시 발생)의 근본적인 원인은 **시크릿 환경 변수의 로드 시점 문제**였습니다.

- **문제 상황:** 프로덕션(ECS) 환경에서는 API 키 등의 민감 정보가 AWS Secrets Manager를 통해 런타임에 주입되어야 합니다. 로직상 `src/api/main.py` 파일의 `create_app()` 함수 내에서 `bootstrap_secrets()`를 호출하여 이를 주입하고 있었습니다.
- **오류 발생 메커니즘:**
  1. `main.py`에서 `bootstrap_secrets()`를 호출하기 **전**에 `from src.api.v1.router import router`가 먼저 실행됨.
  2. 라우터를 임포트하면서 필연적으로 `src/api/dependencies.py` -> `src/patent_agent.py` 및 `src/config.py`가 연쇄적으로 사전 병합 및 임포트됨.
  3. `patent_agent.py`, `config.py`의 최상단에서 모듈 레벨로 선언된 `OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")` 구문들이 평가될 시점에는 아직 시크릿이 로딩되지 않아 빈 문자열(`""`)로 설정되어버림.
  4. 이후 사용자가 `POST /api/v1/analyze`를 호출할 때, 의존성 주입(`get_patent_agent()`) 과정에서 클래스가 초기화되는데 "API KEY가 설정되지 않았다"며 `ValueError`를 발생시킴.
  5. 엔드포인트 도달 전 DI에서 터진 에러는 곧바로 `global_exception_handler`로 잡혀, 화면에는 **500 Internal Server Error**로 표출됨.
- **추가 문제 (Rate Limiter):** 기존 코드 리팩토링 과정 중 `main.py`에 적용되었던 `RateLimitException` 전역 핸들러가 누락된 점을 발견했습니다. 이를 통해 사용자가 사용 횟수 제한을 넘기면 제대로 된 안내(429) 대신 500 에러를 겪게 되는 잠재적인 버그가 있었습니다.

#### 2. 개선 내용
- **`bootstrap_secrets()` 호출 시점 변경:** `src/api/main.py` 최상단(fastapi 등 서드파티 모듈 임포트 직후)으로 `bootstrap_secrets()` 실행 위치를 이동시켰습니다. 이제 애플리케이션 내부 로직 모듈(`src.~`)이 임포트되기 전에 환경 변수 주입이 먼저 보장됩니다.
- **`RateLimitException` 핸들러 복원:** 사용량이 초과되었을 때 명확한 메시지와 함께 429 Too Many Requests 상태 코드가 내려가도록 핸들러를 추가 복원했습니다.

---

### 📋 PM 및 DevOps 전달용 백로그
- **Epic: RAG 로직 고도화 (Backend)**
  - [ ] 시크릿 환경 변수 및 `.env` 로딩 우선순위를 개선하고 테스트 코드를 통한 검증 프로세스 추가 고려
- **Epic: FastAPI 웹 서비스화 (Backend)**
  - [x] 부트스트랩 시크릿 로딩 시점 최상단 배치를 통한 API Key 부재에 의한 500 Error Fix
  - [x] 누락된 Rate Limiter Exception 전역 핸들러 복원
- **Epic: 컨테이너 및 인프라 구축 (DevOps에게 전달할 사항)**
  - [ ] GitHub Actions 또는 ECS Task 내 앱 로그 상에서 "Failed to load secrets initially" 경고 메시지가 발생하지 않는지 모니터링 필요 (boto3 모듈 등 종속성 문제 점검)
