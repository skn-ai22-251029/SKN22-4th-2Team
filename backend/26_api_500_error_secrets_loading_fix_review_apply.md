### 🛠️ 코드베이스 분석 결과
이번 리뷰 피드백(`26_api_500_error_secrets_loading_fix_review.md`) 기반으로, API 내부의 500 에러 및 비밀키 로딩 순서에 대한 구조적 결함(Hardcaching 안티패턴)과 런타임 보안/안정성을 해결했습니다.

**주요 수정 사항:**
1. **환경변수 하드캐싱 안티패턴 제거 (`src/patent_agent.py`)**  
   - 모듈 최상단에서 `os.environ.get()`을 직접 호출하여 캐싱하던 것을 삭제했습니다. 싱글톤 패턴과 동적 로딩을 방해하던 잠재적 버그 요인을 제거했습니다.
2. **설정 일원화 및 단일 진입점 확보 (`src/config.py`)**  
   - 분산된 `load_dotenv()` 호출을 정리하고, `AgentConfig` 클래스를 추가해 `OPENAI_API_KEY`, 언어 모델 종류(`EMBEDDING_MODEL` 등) 및 필터링 수치 제어(`GRADING_THRESHOLD` 등)를 하나의 `config` 인스턴스로 관리하도록 개편했습니다.
3. **API Fast-Fail 로직 반영 (`src/api/main.py`)**  
   - `bootstrap_secrets()` 과정에서 에러가 발생한 경우 단순히 Warning만 띄우던 동작을 `sys.exit(1)` 및 `critical` 패닉으로 수정했습니다. 이제 AWS 환경이나 시크릿 로딩에 실패한 경우 즉시 컨테이너가 중단돼, 프록시(L4/L7 ALB)의 상태 점검 통과를 방지해 보안 이슈를 예방합니다.

### 📋 PM 및 DevOps 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: RAG 로직 고도화 (Backend)**
  - [x] RAG 모듈 레벨의 환경변수 캐싱 로직 삭제 구조화 완료 (`patent_agent.py`)
- **Epic: FastAPI 웹 서비스화 (Backend)**
  - [x] Secrets 부트스트래핑 실패 시 Fast-Fail(비정상 종료) 로직 적용
- **Epic: 컨테이너 및 인프라 구축 (DevOps에게 전달할 사항)**
  - [ ] 컨테이너 시작 시 비밀키 가져오기 단계에서 `sys.exit(1)` 발생 시, 무한 재시작 방지 위한 ALB 헬스체크 임계치 테스트 요청
