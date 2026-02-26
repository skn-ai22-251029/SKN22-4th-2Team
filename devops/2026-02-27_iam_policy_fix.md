# [2026-02-27] ECS 배포 권한 에러(iam:PassRole, ecs:RegisterTaskDefinition) 해결 가이드

## 주요 문제 사항
최근 Production 배포 파이프라인의 `ECS Task Definition 리비전 등록` 단계에서 다음과 같은 에러가 발생했습니다:
1. **에러 내용**: `User: arn:aws:sts::***:assumed-role/github-actions-oidc-role/... is not authorized to perform: ecs:RegisterTaskDefinition on resource...`
2. **원인 분석**:
   - 에러 메시지에 명확히 나와 있듯이, GitHub Actions가 OIDC 방식을 통해 발급받아 사용하는 AWS IAM 역할(**`github-actions-oidc-role`**)에 ECS Task Definition을 새롭게 등록(Register)할 권한이 없기 때문입니다.
   - 단지 ECR에 이미지를 푸시하는 권한(`AmazonEC2ContainerRegistryPowerUser` 등)만 설정되어 있고, ECS에 새로운 배포를 지시하는 권한 정책(Policy)이 역할에 부여되어 있지 않은 상태입니다.

## 해결 방법
AWS 콘솔에 접속하여 **`github-actions-oidc-role`** IAM 역할에 ECS 배포를 위한 추가 권한을 부여해야 합니다.

### 조치 절차 (AWS IAM 설정)
1. **AWS Console** 로그인 후 **IAM > 역할(Roles)** 메뉴로 이동합니다.
2. `github-actions-oidc-role` 역할을 검색하여 클릭합니다.
3. [권한(Permissions)] 탭에서 **[권한 추가(Add permissions)] > [인라인 정책 생성(Create inline policy)]** 을 선택합니다.
4. 정책 편집기를 **JSON** 뷰로 전환하고, 아래의 정책 코드를 복사해서 붙여넣습니다.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RegisterTaskDefinition",
            "Effect": "Allow",
            "Action": [
                "ecs:RegisterTaskDefinition",
                "ecs:DescribeTaskDefinition",
                "ecs:DeregisterTaskDefinition"
            ],
            "Resource": "*"
        },
        {
            "Sid": "PassRoleToECS",
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/shortcut-ecs-task-role",
                "arn:aws:iam::*:role/ecsTaskExecutionRole"
            ],
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "ecs-tasks.amazonaws.com"
                }
            }
        },
        {
            "Sid": "UpdateService",
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices"
            ],
            "Resource": [
                "arn:aws:ecs:*:*:service/*/*"
            ]
        }
    ]
}
```

5. **`iam:PassRole`** 부분의 Resource ARN은 `infra/ecs/task-definition-template.json`에 정의된 `taskRoleArn` 및 `executionRoleArn`과 일치시켰습니다.
6. 정책 이름을 적절히 지정(예: `GitHubActions-ECSDeploy-Policy`)하고 정책을 생성 및 역할에 연결(Attach)합니다.

이렇게 IAM 권한 설정을 한 번만 추가해 주시면, 권한 부족 에러가 사라지고 새 Task Definition 등록 및 Update Service까지 정상적으로 진행될 것입니다!

---

### 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: CI/CD 및 인프라 보안**
  - [ ] AWS IAM에서 `github-actions-oidc-role` 역할에 ECS 배포 권한(`ecs:RegisterTaskDefinition`, `ecs:UpdateService`) 및 `iam:PassRole` 권한을 담은 인라인 정책 추가 및 연결 권고
