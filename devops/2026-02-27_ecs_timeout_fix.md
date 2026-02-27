# [2026-02-27] ECS 배포 TIMEOUT 이슈 (ECR Pull 및 CloudWatch Log 권한) 트러블슈팅 리포트

## 주요 문제 사항
이번에는 ECS에 배포가 시도되었지만, 새 컨테이너 Task가 정상적으로 실행되지 못해 서비스 안정화 대기시간을 초과하여 **TIMEOUT 에러**가 발생했습니다. 직접 AWS CLI를 통해 중지된 Task의 에러 로그를 분석한 결과, 아래 두 가지 핵심 동작에서 실패가 발생하고 있었습니다.

### 1. ECR 이미지 Pull Timeout
- **에러 로그**: `unable to pull secrets or registry auth: The task cannot pull registry auth from Amazon ECR... i/o timeout`
- **원인 분석**: 현재 `short-cut-prod-cluster` 안의 서비스는 4개의 서브넷을 모두 사용하도록 구성되어 있습니다. 그 중 2개의 서브넷은 외부 인터넷망으로 나가는 라우팅 경로(IGW 등)가 없는 완전한 **프라이빗(Private) 서브넷**이었습니다. 컨테이너가 이 프라이빗 서브넷에 배치(Scheduling)되었을 때, 인터넷을 통해 ECR에서 도커 이미지를 다운로드하려고 하나, 네트워크가 막혀있어 영구적인 타임아웃이 발생했습니다.
- **조치 사항**: AWS ECS `short-cut-api-service-d7flqqqv` 서비스 설정을 제가 CLI를 통해 직접 수정하여, 인터넷 통신 방이 열려있는 **퍼블릭(Public) 서브넷 2개 (`subnet-09e89e81bd250c717`, `subnet-011b3e0a89be6542b`)에만 Task가 생성되도록 네트워크 구성을 제한(Update)**해 드렸습니다.

### 2. CloudWatch Log Group 생성 권한 및 리전 오류
- **에러 로그**: `failed to create Cloudwatch log group... User: ecsTaskExecutionRole is not authorized to perform: logs:CreateLogGroup on resource: arn:aws:logs:us-east-1...`
- **원인 분석**: 
   - `infra/ecs/task-definition-template.json` 파일에 AWS 리전이 `us-east-1`(미국)으로 하드코딩 되어 있었고, `awslogs-create-group: "true"` 라는 자동 로그그룹 생성 옵션이 켜져 있었습니다.
   - 반면 이 프로젝트가 운영되는 실제 리전은 서울(`ap-northeast-2`)이었으며, 가장 중요한 이슈로 ECS Task 구동 IAM 권한(`ecsTaskExecutionRole`)에는 `logs:CreateLogGroup` (새로운 로그 그룹을 만드는 권한)이 없어 에러가 나며 컨테이너가 바로 죽어버리는 현상이 발생했습니다.
- **조치 사항**: 
   1. `aws CLI`를 이용해 서울(`ap-northeast-2`) 리전에 수동으로 `/ecs/short-cut-api` 로그 그룹을 프리-프로비저닝(생성) 완료해두었습니다.
   2. 파이프라인의 에러가 나지 않도록 `infra/ecs/task-definition-template.json`의 내용을 **`ap-northeast-2`로 동기화**하였으며, 권한 에러를 야기하는 `awslogs-create-group` 속성은 삭제했습니다.

---

## 🚀 다음 단계 (Action Item)
- 제가 ECS 네트워크 환경 설정부터 코드 수정, CloudWatch 기반 생성까지 모두 조치해 두었습니다.
- **사용자님께서는 방금 제가 변경한 로컬의 `infra/ecs/task-definition-template.json` 파일을 커밋하고, 다시 한번 `develop` 브랜치에 푸시해 주시기 바랍니다.** 이번에는 타임아웃 없이 무사히 컨테이너가 뜰 것입니다!

### 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: CI/CD 및 인프라 디버깅**
  - [x] 프라이빗 서브넷에 배치된 Fargate Task의 ECR 풀링 타임아웃 현상을 막기 위해, ECS 서비스의 서브넷을 2개의 퍼블릭 서브넷(IGW 연결망)으로 수정 (`aws ecs update-service`)
  - [x] Task-Definition 템플릿의 리전을 `ap-northeast-2`로 수정 및 `CreateLogGroup` 권한 누락으로 인한 컨테이너 충돌 방울 처리 완료 (수동 CloudWatch Group 프로비저닝 완료)
