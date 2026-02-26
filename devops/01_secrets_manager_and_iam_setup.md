# [DevOps] AWS Secrets Manager 시크릿 등록 & IAM Task Role 연결 가이드

> **작성일:** 2026-02-25  
> **담당:** DevOps (리드 클라우드 & DevOps 엔지니어)  
> **Epic:** 컨테이너 및 인프라 구축  
> **선행 작업:** Backend Issue #8 코드 구현 완료 (`src/secrets_manager.py`, IAM 정책 파일 3종)

---

## 📋 개요

Backend 에이전트가 구현한 `src/secrets_manager.py`와 IAM 정책 파일(`infra/iam/`)을 기반으로,
AWS 콘솔에서 실제 시크릿을 등록하고 ECS Task Role에 최소 권한 정책을 연결하는 단계를 정리합니다.

### 작업 범위
| # | 작업 항목 | 상태 |
|---|---------|------|
| 1 | AWS Secrets Manager에 `short-cut/prod/app` 시크릿 등록 | ✅ 가이드 완성 |
| 2 | IAM Task Role 생성 및 정책 연결 | ✅ 가이드 완성 |
| 3 | ECS Task Definition에 환경 변수 설정 | ✅ 가이드 완성 |
| 4 | 시크릿 로테이션(Rotation) 전략 수립 | ✅ 가이드 완성 |
| 5 | 시크릿 접근 검증 (로컬 테스트) | ✅ 가이드 완성 |

---

## 1. AWS Secrets Manager에 시크릿 등록

### 1-1. 시크릿 구조 (네이밍 컨벤션)

```
시크릿 이름: short-cut/prod/app
리전:       us-east-1
암호화 키:   aws/secretsmanager (기본 KMS) — 비용 최적화
```

**네이밍 컨벤션 규칙:**
```
{프로젝트}/{환경}/{구분}
  ├── short-cut/prod/app       ← 프로덕션 앱 시크릿 (현재)
  ├── short-cut/staging/app    ← 스테이징 (향후)
  └── short-cut/prod/db        ← DB 전용 (향후, 필요 시 분리)
```

### 1-2. 등록할 JSON 값

`infra/iam/secret-structure-example.json`을 참고하여 아래 JSON을 등록합니다.

> ⚠️ **절대 주의:** 아래 값은 예시입니다. 실제 API Key를 코드나 문서에 하드코딩하지 마세요.

```json
{
    "OPENAI_API_KEY": "sk-실제키를입력하세요",
    "PINECONE_API_KEY": "pcsk_실제키를입력하세요",
    "GCP_PROJECT_ID": "실제-GCP-프로젝트-ID",
    "GOOGLE_APPLICATION_CREDENTIALS_JSON": "{\"type\":\"service_account\",\"project_id\":\"...\",\"private_key_id\":\"...\",\"private_key\":\"-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n\",\"client_email\":\"...\",\"client_id\":\"...\",\"auth_uri\":\"https://accounts.google.com/o/oauth2/auth\",\"token_uri\":\"https://oauth2.googleapis.com/token\",\"auth_provider_x509_cert_url\":\"https://www.googleapis.com/oauth2/v1/certs\",\"client_x509_cert_url\":\"...\"}",
    "APP_SECRET_KEY": "랜덤-시크릿-키-생성값",
    "MILVUS_HOST": "프로덕션-Milvus-호스트",
    "MILVUS_PORT": "19530"
}
```

### 1-3. AWS 콘솔 등록 Step-by-Step

```
1️⃣  AWS Management Console → Secrets Manager → "Store a new secret" 클릭

2️⃣  Secret type 선택
    → "Other type of secret" 선택

3️⃣  Key/value pairs
    → "Plaintext" 탭 선택 → 위 JSON 내용 전체를 붙여넣기
    
4️⃣  Encryption key
    → "aws/secretsmanager" (Default) 선택 (추가 비용 없음)

5️⃣  Secret name
    → short-cut/prod/app  (정확히 이 이름으로 입력)

6️⃣  Description (선택)
    → "쇼특허(Short-Cut) 프로덕션 앱 시크릿 – API Keys, GCP 자격증명 통합"

7️⃣  Tags (권장)
    → Project: short-cut
    → Environment: prod
    → ManagedBy: devops

8️⃣  Rotation → "Disable automatic rotation" (초기 단계, 수동 관리)
    → 향후 로테이션 전략은 섹션 4 참조

9️⃣  Review → "Store" 클릭
```

### 1-4. AWS CLI 대안 (자동화 시)

```bash
# 시크릿 생성 (JSON 파일 기반)
aws secretsmanager create-secret \
    --name "short-cut/prod/app" \
    --description "쇼특허(Short-Cut) 프로덕션 앱 시크릿" \
    --secret-string file://secrets-values.json \
    --region us-east-1 \
    --tags '[
        {"Key":"Project","Value":"short-cut"},
        {"Key":"Environment","Value":"prod"},
        {"Key":"ManagedBy","Value":"devops"}
    ]'

# ⚠️ secrets-values.json은 실제 키 값이 들어있으므로
#    절대로 Git에 추가하지 마세요. 사용 후 즉시 삭제합니다.
```

```bash
# 시크릿 등록 확인
aws secretsmanager describe-secret \
    --secret-id "short-cut/prod/app" \
    --region us-east-1
```

```bash
# 값 확인 (필요 시)
aws secretsmanager get-secret-value \
    --secret-id "short-cut/prod/app" \
    --region us-east-1 \
    --query SecretString \
    --output text | python -m json.tool
```

---

## 2. IAM Task Role 생성 및 정책 연결

### 2-1. 아키텍처 이해

```
ECS Task Definition
  │
  ├── taskRoleArn       ← 앱 컨테이너가 AWS 서비스에 접근할 때 사용
  │     └── shortcut-ecs-task-role  (Secrets Manager 접근용)
  │           ├── Trust Policy:     ecs-task-trust-policy.json
  │           └── Inline Policy:    secrets-read-policy.json
  │
  └── executionRoleArn  ← ECS가 컨테이너 이미지를 풀/로그 전송에 사용
        └── ecsTaskExecutionRole  (AWS 관리 정책 사용)
```

### 2-2. Task Role 생성 (AWS 콘솔)

```
1️⃣  IAM → Roles → "Create role"

2️⃣  Trusted entity type
    → "Custom trust policy" 선택
    → infra/iam/ecs-task-trust-policy.json 내용 붙여넣기:
```

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECSTasksAssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

```
3️⃣  Permissions → "Create inline policy" 선택 → JSON 탭
    → infra/iam/secrets-read-policy.json 내용 붙여넣기:
```

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ReadShortCutAppSecret",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:short-cut/prod/app-*"
        },
        {
            "Sid": "DecryptWithCMKViaSecretsManager",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "arn:aws:kms:us-east-1:*:key/*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com"
                }
            }
        }
    ]
}
```

```
4️⃣  인라인 정책 이름
    → ShortCutSecretsReadPolicy

5️⃣  Role name
    → shortcut-ecs-task-role

6️⃣  Description
    → "쇼특허 ECS Task Role – Secrets Manager 읽기 전용"

7️⃣  Tags (권장)
    → Project: short-cut
    → Environment: prod

8️⃣  "Create role" 클릭
```

### 2-3. Task Role 생성 (AWS CLI 대안)

```bash
# 1. Trust Policy로 역할 생성
aws iam create-role \
    --role-name shortcut-ecs-task-role \
    --assume-role-policy-document file://infra/iam/ecs-task-trust-policy.json \
    --description "쇼특허 ECS Task Role – Secrets Manager 읽기 전용" \
    --tags '[{"Key":"Project","Value":"short-cut"},{"Key":"Environment","Value":"prod"}]'

# 2. 인라인 정책 연결
aws iam put-role-policy \
    --role-name shortcut-ecs-task-role \
    --policy-name ShortCutSecretsReadPolicy \
    --policy-document file://infra/iam/secrets-read-policy.json

# 3. 확인
aws iam get-role --role-name shortcut-ecs-task-role
aws iam get-role-policy \
    --role-name shortcut-ecs-task-role \
    --policy-name ShortCutSecretsReadPolicy
```

### 2-4. ⚠️ Resource ARN 하드코딩 주의

현재 `secrets-read-policy.json`의 Resource에 `*`(와일드카드)가 AWS Account ID 위치에 있습니다:
```
arn:aws:secretsmanager:us-east-1:*:secret:short-cut/prod/app-*
```

**프로덕션 강화 시** 실제 AWS Account ID로 교체하는 것을 권장합니다:
```
arn:aws:secretsmanager:us-east-1:123456789012:secret:short-cut/prod/app-*
```

> 시크릿 ARN 끝의 `-*`은 Secrets Manager가 자동 추가하는 6자리 랜덤 접미사를 포함하기 위함입니다.

---

## 3. ECS Task Definition 환경 변수 설정

ECS Task Definition에서 **민감하지 않은 환경 변수**를 평문으로 설정합니다.
(실제 API 키 등은 `bootstrap_secrets()`가 런타임에 Secrets Manager에서 로드합니다.)

### 3-1. Task Definition Container Definitions에 추가할 환경 변수

```json
{
    "containerDefinitions": [
        {
            "name": "short-cut-api",
            "image": "<ECR_URI>:latest",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "APP_ENV",
                    "value": "production"
                },
                {
                    "name": "AWS_REGION",
                    "value": "us-east-1"
                },
                {
                    "name": "SECRET_NAME",
                    "value": "short-cut/prod/app"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/short-cut-api",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ],
    "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/shortcut-ecs-task-role",
    "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024"
}
```

### 3-2. 시크릿 주입 흐름 (End-to-End)

```
Container Start
  │
  ├─ entrypoint.sh (fail-fast 검증)
  │   ├─ APP_ENV=production → AWS_REGION 필수 검증
  │   └─ SECRET_NAME 기본값: short-cut/prod/app
  │
  └─ Python App 시작 (uvicorn → main.py → config.py)
      │
      └─ bootstrap_secrets() 호출
          ├─ boto3 → Secrets Manager → GetSecretValue
          ├─ JSON 파싱 → os.environ 주입
          ├─ GOOGLE_APPLICATION_CREDENTIALS_JSON → 임시 파일 생성
          └─ update_config_from_env() → config 인스턴스 동기화
```

---

## 4. 시크릿 로테이션(Rotation) 전략

### 4-1. 현 단계: 수동 로테이션 (Phase 1)

초기 배포 단계에서는 AWS 콘솔을 통한 수동 로테이션을 권장합니다.

```
로테이션 주기:  90일 (분기별)
담당:          DevOps 엔지니어
절차:
  1. AWS 콘솔 → Secrets Manager → short-cut/prod/app
  2. "Retrieve secret value" → "Edit"
  3. 변경할 키의 새 값 입력 (예: OPENAI_API_KEY 갱신)
  4. "Save" → ECS 서비스 재시작 (Force new deployment)
  5. CloudWatch 로그에서 "시크릿 로드 성공" 메시지 확인
```

### 4-2. 향후: 자동 로테이션 (Phase 2)

서비스 안정화 후 Lambda 기반 자동 로테이션으로 전환합니다.

```
구성 요소:
  ├── Lambda Function: shortcut-secret-rotation
  │     └── 외부 API Provider에서 새 키 발급 → Secrets Manager 업데이트
  ├── Secrets Manager Rotation Schedule: 30일
  └── CloudWatch Alarm: 로테이션 실패 시 SNS 알림
  
대상 키별 전략:
  ├── OPENAI_API_KEY      → OpenAI 대시보드에서 새 키 발급 후 교체
  ├── PINECONE_API_KEY    → Pinecone 콘솔에서 새 키 발급 후 교체
  ├── GCP 서비스 계정     → GCP IAM에서 새 키 JSON 생성 후 교체
  └── APP_SECRET_KEY      → 랜덤 생성 (secrets.token_urlsafe(64))
```

### 4-3. 로테이션 시 무중단 배포 고려

```
권장 패턴: Blue/Green 시크릿 교체
  1. 새 API Key 발급 (이전 키도 유효 상태 유지)
  2. Secrets Manager에 새 값 업데이트
  3. ECS Force New Deployment → 새 Task가 새 시크릿으로 부트스트랩
  4. 헬스체크 통과 확인 후 이전 API Key 폐기
  5. 롤백 필요 시: Secrets Manager 버전 복원 → 재배포
```

---

## 5. 시크릿 접근 검증 (로컬 테스트)

### 5-1. AWS CLI로 시크릿 접근 테스트

```bash
# AWS 자격증명이 설정된 상태에서:
aws secretsmanager get-secret-value \
    --secret-id "short-cut/prod/app" \
    --region us-east-1 \
    --query SecretString \
    --output text | python -m json.tool
```

### 5-2. Python으로 시크릿 로드 테스트

```bash
# 로컬에서 프로덕션 모드 시뮬레이션
APP_ENV=production AWS_REGION=us-east-1 python -c "
from src.secrets_manager import bootstrap_secrets
import os
bootstrap_secrets()
print('OPENAI_API_KEY 로드:', 'OK' if os.getenv('OPENAI_API_KEY') else 'FAIL')
print('PINECONE_API_KEY 로드:', 'OK' if os.getenv('PINECONE_API_KEY') else 'FAIL')
print('GCP_PROJECT_ID 로드:', 'OK' if os.getenv('GCP_PROJECT_ID') else 'FAIL')
"
```

### 5-3. IAM Role 시뮬레이션 (로컬에서 Task Role 테스트)

```bash
# Task Role로 AssumeRole 테스트
CREDS=$(aws sts assume-role \
    --role-arn "arn:aws:iam::<ACCOUNT_ID>:role/shortcut-ecs-task-role" \
    --role-session-name "local-test" \
    --output json)

export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDS | jq -r '.Credentials.SessionToken')

# Task Role 권한으로 시크릿 접근 테스트
aws secretsmanager get-secret-value \
    --secret-id "short-cut/prod/app" \
    --region us-east-1

# 테스트 후 임시 자격증명 정리
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

---

## 6. 보안 체크리스트

| # | 점검 항목 | 상태 |
|---|---------|------|
| 1 | 시크릿 이름이 정확히 `short-cut/prod/app`인지 확인 | ⬜ |
| 2 | 시크릿 JSON에 모든 필수 키가 포함되었는지 확인 | ⬜ |
| 3 | 시크릿이 `us-east-1` 리전에 생성되었는지 확인 | ⬜ |
| 4 | IAM Task Role 신뢰 정책에 `ecs-tasks.amazonaws.com`만 허용되는지 확인 | ⬜ |
| 5 | 인라인 정책 Resource ARN이 `short-cut/prod/app-*`으로 제한되는지 확인 | ⬜ |
| 6 | KMS 조건이 `secretsmanager.us-east-1.amazonaws.com` ViaService로 제한되는지 확인 | ⬜ |
| 7 | Task Definition의 `taskRoleArn`이 올바르게 설정되었는지 확인 | ⬜ |
| 8 | CloudWatch Logs 그룹 `/ecs/short-cut-api`가 생성되었는지 확인 | ⬜ |
| 9 | `.env` 파일이 `.gitignore`에 포함되었는지 확인 | ⬜ |
| 10 | `entrypoint.sh`가 LF(Unix) 라인 엔딩인지 확인 | ⬜ |

---

## 7. 트러블슈팅

### 7-1. `AccessDeniedException` 발생 시

```
원인: Task Role에 Secrets Manager 접근 권한이 없음
해결:
  1. ECS Task Definition의 taskRoleArn 확인
  2. IAM Role에 ShortCutSecretsReadPolicy 인라인 정책이 연결되었는지 확인
  3. 정책의 Resource ARN이 시크릿 ARN과 일치하는지 확인
     (시크릿 ARN: arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:short-cut/prod/app-XXXXXX)
```

### 7-2. `ResourceNotFoundException` 발생 시

```
원인: 시크릿이 존재하지 않거나 리전이 다름
해결:
  1. SECRET_NAME 환경 변수가 "short-cut/prod/app"인지 확인
  2. AWS_REGION 환경 변수가 "us-east-1"인지 확인
  3. AWS 콘솔에서 해당 리전에 시크릿이 존재하는지 확인
```

### 7-3. `ImportError: boto3가 설치되어 있지 않습니다` 발생 시

```
원인: requirements-api.txt에서 boto3가 누락됨
해결: requirements-api.txt에 boto3>=1.34.0, botocore>=1.34.0 확인
      (현재 이미 추가 완료 상태)
```

---

## 📌 참조 파일

| 파일 경로 | 설명 |
|----------|------|
| `infra/iam/secret-structure-example.json` | Secrets Manager 등록용 JSON 구조 예시 |
| `infra/iam/secrets-read-policy.json` | Task Role 인라인 정책 (최소 권한) |
| `infra/iam/ecs-task-trust-policy.json` | Task Role 신뢰 정책 |
| `src/secrets_manager.py` | 시크릿 부트스트랩 Python 모듈 |
| `entrypoint.sh` | 컨테이너 엔트리포인트 (fail-fast 검증) |
| `docker-compose.yml` | 로컬 개발용 Compose (APP_ENV=local) |
| `.env.example` | 환경 변수 템플릿 |
