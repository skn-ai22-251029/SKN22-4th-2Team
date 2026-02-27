# AWS ECS Task Definition 및 Backend 헬스 체크 문제 해결 가이드

현재 발생 중인 `.env` 파일 부재 시 컨테이너 패닉(`sys.exit(1)`) 문제로 인한 **ECS CrashLoopBackOff** 장애를 해결하기 위한 DevOps 가이드입니다. 

우리는 로컬 `.env` 파일을 배포 환경에 포함하지 않고, **AWS Secrets Manager**를 사용하여 보안 값을 주입합니다.

---

## 1. AWS ECS Fargate에서의 환경 변수 주입 방식
ECS Fargate는 물리적인 `.env` 파일을 컨테이너 내부에 생성하지 않습니다. 대신, **Task Definition**의 `secrets` 설정을 통해 컨테이너 기동 시점에 OS 환경 변수(Environment Variables)로 직접 값을 매핑하여 주입합니다. 

### ECS Task Definition 설정 예시 (`task-definition.json`)
```json
{
  "containerDefinitions": [
    {
      "name": "shortcut-backend-container",
      "image": "<ECR_REPOSITORY_URI>:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:shortcut-prod-secrets-XYZ"
        },
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:shortcut-prod-secrets-XYZ"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/shortcut-backend",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole"
}
```
*설명:* 위와 같이 `secrets` 항목에서 지정하면, 컨테이너 실행 시 파이썬 앱 내에서 `os.environ.get('OPENAI_API_KEY')`를 통해 값에 접근할 수 있게 됩니다.

---

## 2. Backend 에이전트를 위한 코드 수정 지침 (문제 해결법)

Backend 팀은 `.env` 파일의 유무로 애플리케이션의 정상 기동 여부를 판단해서는 **절대 안 됩니다**.

### 🚫 기존의 잘못된 방식 (수정 대상)
```python
import os
import sys

# 에러 원인: ECS에는 .env 파일이 없으므로 항상 패닉 발생
if not os.path.exists(".env"):
    print("Error: .env file not found!")
    sys.exit(1)
```

### ✅ 올바른 클라우드 네이티브 방식 (적용해야 할 방식)
```python
import os
import sys

# 해결 방법: 필수 환경 변수가 로드(os.environ)되어 있는지만 확인
def bootstrap_secrets():
    # AWS Secrets Manager가 값을 주입했다면 os.getenv를 통해 조회 가능합니다.
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        # 이 경우에만 진짜 키 누락으로 판단하고 패닉을 발생시킵니다.
        raise ValueError("Critical: OPENAI_API_KEY environment variable is missing!")
```

---

## 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: RAG 로직 고도화 및 배포 최적화 (Backend/PM)**
  - [ ] **🚀 긴급 조치:** `.env` 파일의 물리적 존재 유무를 검사하는 로직(`os.path.exists('.env')` 등)을 애플리케이션 시작(Bootstrapping) 코드에서 완전히 제거
  - [ ] OS 환경 변수인 `os.getenv('OPENAI_API_KEY')`의 값 자체가 비어있는지(`None` 또는 `""`)만 확인하여 패닉(`sys.exit(1)` 또는 `ValueError`)을 발생시키도록 안전하게 수정
- **Epic: AWS 인프라 프로비저닝 (DevOps)**
  - [ ] AWS Secrets Manager 기반 비밀 값 등록 및 Task Definition의 `secrets` 매핑 구성 (Zero Hardcoding)
