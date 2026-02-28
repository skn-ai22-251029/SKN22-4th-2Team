# ☁️ AWS ECS 배포를 위한 인프라 세팅 계획

AWS 인프라, Docker 배포, 그리고 GitHub Actions를 통한 CI/CD 환경 구축 계획입니다.
프로젝트의 특성상 로컬 `.env` 파일을 사용하지 않고 **AWS Secrets Manager**를 통해 환경 변수를 관리하도록 구성하였습니다.

### ☁️ 클라우드 배포 아키텍처 제안
1. **네트워크 인프라 (VPC & Subnets):** 안정성과 보안을 위해 VPC 생성 및 ALB 접속용 Public 서브넷, 그리고 Fargate 컨테이너용 Private/Public 서브넷 분리 구성
2. **컨테이너 레지스트리 (ECR):** CI 파이프라인에서 빌드된 Backend 도커 이미지를 보관하기 위한 전용 ECR 리포지토리 구성
3. **컴퓨팅 서비스 (ECS on Fargate):** 초기 인프라 유지 관리 최소화 및 비용 최적화를 위해 서버리스 컨테이너 서비스인 AWS Fargate 채택
4. **로드 밸런서 (ALB):** 클라이언트 API 요청을 다중 Task로 분산 라우팅 및 무중단 상태 검사(Health Check) 수행
5. **보안 및 환경 변수 (IAM & Secrets Manager):** 
   - AWS Secrets Manager 또는 Parameter Store를 활용해 DB 패스워드나 `OPENAI_API_KEY` 같은 민감 정보를 중앙 집중식으로 안전 관리
   - ECS Task Execution Role에 Secrets Manager 리드 권한을 부여하고, Task Definition의 `secrets` 필드를 통해 환경 변수(ENV) 형태로 컨테이너에 자동 주입
   - **🚨 크리티컬 고려 사항 (Backend 피드백):** 물리적 `.env` 파일 부재를 기준으로 애플리케이션 시작 시 패닉(`sys.exit(1)`)이 발생하도록 로직이 구현된다면, AWS 환경에서는 `.env` 파일 대신 Secrets Manager에서 직접 OS 환경변수를 주입받으므로 **CrashLoopBackOff 무한 재시도 루프** 장애가 발생합니다. 따라서 `os.getenv('OPENAI_API_KEY')` 등으로 실제 필요한 키의 환경변수 존재 자체만 검증하도록 요구됩니다.

### 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: AWS 인프라 프로비저닝 (DevOps)**
  - [ ] 기본 격리 네트워크 구성 (VPC, 서브넷 라우팅 테이블)
  - [ ] ECR 리포지토리 생성 및 로컬 Docker 이미지 수동 Push 검증
  - [ ] AWS Secrets Manager 기반 비밀 값 등록 및 IAM Task Execution Role 정책 추가
  - [ ] ECS 클러스터 및 Fargate Task Definition 작성 (Secrets Manager 매핑, Health Check 설정 반영)
  - [ ] 도메인 매핑 대기 및 포트 포워딩을 위한 ALB(Application Load Balancer) 구성
- **Epic: CI/CD 파이프라인 구축 (DevOps)**
  - [ ] GitHub Actions OIDC 연결 세팅 (AWS Long-term Access Key 하드코딩 완전 배제)
  - [ ] 자동화 배포를 위한 `.github/workflows/deploy.yml` 스크립트 작성 (ECS Blue/Green 또는 Rolling Update)
- **Epic: Backend 시스템 검증 및 패치 (Backend)**
  - [ ] ECS 환경에서의 실행을 위해 물리적 `.env` 파일 존재 여부 검사 로직을 제거하고, 핵심 `OS 환경 변수(env vars)` 자체의 초기화 여부만 검증하도록 수정 요청
