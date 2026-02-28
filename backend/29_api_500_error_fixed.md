### 🛠️ 코드베이스 분석 결과

원인 분석을 위해 시뮬레이션을 돌려본 결과, 500 API 에러와 배포(Rollback) 실패의 근본 원인은 **AWS Secrets Manager 접근 권한 및 환경 변수 주입 타이밍의 불일치**입니다.

1.  **기존 배포가 남겼던 API 500 에러의 원인 (Old Version)**
    *   기존 코드에서는 `secrets_manager.py`가 AWS Secrets Manager로부터 시크릿을 불러오지 못하더라도(권한 부족 등) 조용히(Silently) 에러 핸들링을 넘기고 서버를 구동시켰습니다.
    *   이로 인해 필수 키(`OPENAI_API_KEY`, `PINECONE_API_KEY`)가 없는 상태로 서버가 실행되었고, 사용자가 "분석 시작하기" 버튼을 눌렀을 때 `PineconeClient`나 `PatentAgent`가 초기화되면서 뒤늦게 예외(Exception)를 발생시켰습니다.
    *   이 예외가 스트리밍 응답이 시작되기 전에 발생하여, Frontend로 `HTTP 500 Internal Server Error`가 반환된 것입니다.

2.  **현재 배포가 20분씩 지연되며 실패하는 원인 (New Version)**
    *   이전 세션에서 이 문제를 해결하고자 `main.py`의 `lifespan`에 **Fail-Fast(조기 실패)** 로직을 추가했습니다. (필수 키가 없으면 서버 시작 불가)
    *   그러나 현재 ECS Task 환경에서 애플리케이션(Python)이 `boto3`를 이용해 Secrets Manager를 직접 호출하려고 할 때, **Task Role(작업 역할)**에 `secretsmanager:GetSecretValue` 권한이 없어서 예외가 발생합니다.
    *   이로 인해 애플리케이션 시작이 차단(`sys.exit(1)`)되고, ECS는 컨테이너가 정상 구동되지 않았다고 판단하여 헬스체크 대기 후 **롤백(배포 실패)**을 무한 반복하게 됩니다.

3.  **해결 방안 및 반영 내역**
    *   **코드 레벨 수정 완료:** ECS에서 자체적으로 환경 변수 주입(Native Secret Injection)을 완료한 경우, 애플리케이션 내의 `boto3` SDK 로출 로직을 건너뛰도록 `src/secrets_manager.py`를 수정했습니다. 이제 ECS가 올바르게 주입해주기만 하면 파이썬 에러 없이 앱이 뜹니다.
    *   **인프라 점검 필요:** DevOps 에이전트가 ECS Task Definition에 Secrets를 올바르게 연결했는지, 혹은 Task IAM Role 권한이 부여되었는지 점검해야 합니다. (제 백엔드 코드의 책임 범위를 넘어선 인프라 부분입니다).

---

### 📋 PM 및 DevOps 전달용 백로그
- **Epic: RAG 로직 고도화 (Backend)**
  - [x] API 500 에러 추적을 위한 로컬 시뮬레이션 및 로직 예외 처리
  - [x] ECS 배포가 롤백되지 않도록 `secrets_manager.py` 분기 최적화 (Native Injection 우대)
- **Epic: 컨테이너 및 인프라 구축 (DevOps에게 전달할 사항)**
  - [ ] ECS Task Definition에서 `secrets` 블록을 통하여 `OPENAI_API_KEY`, `PINECONE_API_KEY`가 애플리케이션 `os.environ`에 직접 주입되고 있는지 확인 요망
  - [ ] 애플리케이션이 직접 `boto3`를 사용할 필요가 없다면 ECS Native 방식 유지. 단, 앱에서 직접 호출이 필요하다면 ECS Task Role에 `secretsmanager:GetSecretValue` 정책 추가 요망
