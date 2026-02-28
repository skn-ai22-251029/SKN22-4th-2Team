### 🛠️ 코드베이스 분석 결과 (API 500 에러 근본 원인 파악)

현재 `src/patent_agent.py` 레벨에서 `os.environ.get()` 하드캐싱을 제거하고 `src/api/main.py`에 `sys.exit(1)`을 적용하는 등 보안/안정성 개선이 있었으나, 여전히 브라우저상에서 API 500 에러가 반환되는 근본적인 원인은 **"에러(예외) 발생 시점과 생명 주기(Lifecycle)의 엇갈림"**에 있습니다.

**[상세 원인 분석]**
1. **Secrets Manager의 예외 흡수(Swallowing)**: 
   `src/secrets_manager.py`의 `_load_from_dotenv()` 함수는 로컬 환경(`APP_ENV=local`)에서 `.env` 파일이 없더라도 단순히 `logger.warning`만 출력할 뿐 `Exception`을 발생시키지 않습니다.
2. **Fast-Fail 로직의 우회**:
   이로 인해 `src/api/main.py` 최상단에 작성한 `bootstrap_secrets()`는 에러 없이 "성공"한 것으로 간주되어 `sys.exit(1)`(Fast-Fail)이 트리거되지 않고 서버(uvicorn)가 정상 기동됩니다.
3. **런타임 의존성 주입 시점의 병목**:
   프론트엔드에서 `/api/v1/analyze` 엔드포인트를 호출하는 순간, FastAPI의 `Depends(get_patent_agent)`가 발동되어 `PatentAgent` 싱글톤 객체를 최초로 생성(`__init__`)하려고 시도합니다.
4. **글로벌 예외 핸들러에 의한 500 에러 변환**:
   `PatentAgent().__init__` 과정에서 `config.embedding.api_key`가 빔(`""`)을 확인하고 `ValueError("config.embedding.api_key not set...")`를 던지게 됩니다. 이는 API 라우터 실행 도중 발생한 예외이므로, 글로벌 핸들러인 `global_exception_handler`에 포착되어 결국 프론트엔드에 `HTTP 500 Internal Server Error` 응답을 내려주게 됩니다. 

요약하자면, **백엔드 서버 런타임 직전(App Bootstrapping)에 필수 API 키 누락 검증이 누락**되었기 때문에, 에러가 발생해야 할 시점을 놓치고 **클라이언트가 API를 호출한 시점에서야 비로소 키 누락으로 인한 서버 에러(500)가 터지는 구조**입니다.

### 📋 PM 및 DevOps 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: RAG 로직 고도화 (Backend)**
  - [x] (완료) 모듈별 환경 변수 런타임 하드캐싱 제거 및 `config.py`로 설정 일원화
  - [ ] **필수 키 검증 로직을 앱 시작(Bootstrapping) 시점으로 이동**: `src/api/main.py`에서 `bootstrap_secrets()` 완료 직후, `config` 객체를 조회하여 `OPENAI_API_KEY` 파라미터가 없으면 강제로 `ValueError`를 발생시켜 `sys.exit(1)`을 유도하도록 수정
  - [ ] **의존성 사전 초기화 (Lifespan Context 사용)**: FastAPI의 `@asynccontextmanager` 의존성을 활용해, 모듈 초기 로드 지연을 막고 트래픽 수신 전(Pre-warm) `PatentAgent` 인스턴스를 미리 띄워 앱의 완전성을 검증하도록 리팩토링

- **Epic: 컨테이너 및 인프라 구축 (DevOps에게 전달할 사항)**
  - [ ] (참고) Backend 픽스가 완료되면 로컬 `.env` 부재 시 컨테이너가 즉시 패닉 상태(`sys.exit(1)`)로 내려가도록 바뀔 예정이므로, ALB/ECS 헬스 체크 시 컨테이너 무한 재시도 루프(CrashLoopBackOff) 주의 요망
