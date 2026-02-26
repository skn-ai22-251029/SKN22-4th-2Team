# [DevOps] Issue #8: AWS Secrets Manager 기반 시크릿 주입 구조 구현

## 1. 완료한 작업 내역

### 신규 생성 파일
- **`src/secrets_manager.py`**: 시크릿 주입 유틸리티 모듈
  - `APP_ENV=local` → `dotenv` 로드 (기존 동작 완전 유지)
  - `APP_ENV=production` → AWS Secrets Manager 호출 → `os.environ` 주입
  - **우선순위: Secrets Manager > .env** (production에서는 SM 값이 override)
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON` → 임시 파일로 저장 후 `GOOGLE_APPLICATION_CREDENTIALS` 자동 설정 (GCP SDK 호환)
  - 프로세스 종료 시 임시 파일 자동 삭제 (`atexit`)
- **`entrypoint.sh`**: 컨테이너 엔트리포인트
  - 프로덕션 필수 환경 변수(`AWS_REGION`) 사전 검증 (fail-fast)
  - `exec uvicorn ...` 으로 PID 1 교체 → graceful shutdown 보장
- **`infra/iam/secrets-read-policy.json`**: ECS Task Role 최소 권한 IAM 정책
  - `secretsmanager:GetSecretValue`, `DescribeSecret` — `short-cut/prod/app-*` 리소스만
  - `kms:Decrypt` — Secrets Manager via KMS 경우만 (Condition)
- **`infra/iam/ecs-task-trust-policy.json`**: ECS Task Role 신뢰 정책
- **`infra/iam/secret-structure-example.json`**: Secrets Manager 등록 예시 JSON (콘솔 복사용)
- **`docker-compose.yml`**: 로컬 개발 전용 Compose (APP_ENV=local, env_file: .env)
- **`tests/test_secrets_manager.py`**: 유닛 테스트 (10개 케이스)

### 수정 파일
- **`src/config.py`**: `load_dotenv()` → `bootstrap_secrets()` 교체, `update_config_from_env()`에 `PINECONE_API_KEY` 동기화 추가
- **`Dockerfile`**: `COPY entrypoint.sh` + `chmod +x` + `CMD` → `ENTRYPOINT` 교체
- **`requirements-api.txt`**: `boto3>=1.34.0`, `botocore>=1.34.0` 추가
- **`.env.example`**: `APP_ENV`, `AWS_REGION`, `SECRET_NAME` 변수 설명 추가

### 시크릿 구조 (단일 그룹)
```
short-cut/prod/app  →  JSON 하나에 모든 키 통합
  OPENAI_API_KEY
  PINECONE_API_KEY
  GCP_PROJECT_ID
  GOOGLE_APPLICATION_CREDENTIALS_JSON
  APP_SECRET_KEY
  MILVUS_HOST / MILVUS_PORT
```

## 2. 다음 단계 권장 사항 (DevOps)

- **AWS 콘솔에서 시크릿 등록**: `infra/iam/secret-structure-example.json` 참고해 `short-cut/prod/app` 시크릿 생성
- **IAM Task Role 연결**: `secrets-read-policy.json` → ECS Task Role에 인라인 정책으로 연결, `ecs-task-trust-policy.json`으로 신뢰 관계 설정
- **ECS Task Definition 수정**: `APP_ENV=production`, `AWS_REGION=us-east-1` 환경 변수를 Task Definition에 추가 (민감하지 않은 값이므로 평문 OK)
- **`entrypoint.sh` LF 포맷 확인**: Windows에서 생성되었으므로 빌드 전 `git config core.autocrlf false` 확인 필요

## 3. PM 에이전트 상태 업데이트 요약

- **Issue #8 [AWS Secrets Manager 시크릿 주입 구조 설계]** 코드 구현 완료
  - 이중 구조(로컬 .env ↔ 프로덕션 Secrets Manager) 구현
  - IAM 최소 권한 정책 파일 3종 생성
  - 유닛 테스트 10케이스 커버
- DevOps 에이전트에게 AWS 콘솔 시크릿 등록 및 ECS Task Role 연결 작업 이관 요청
