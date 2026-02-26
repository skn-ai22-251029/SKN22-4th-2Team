# 02. AWS ECR 이미지 빌드/배포 CI/CD 파이프라인 구축

> **Issue #7** | 작성일: 2026-02-25 | 작성자: DevOps Agent

---

## 📁 생성된 파일 목록

| 파일 | 설명 |
|------|------|
| `.github/workflows/ecr-cicd.yml` | GitHub Actions CI/CD 메인 워크플로우 |
| `infra/iam/github-actions-oidc-policy.json` | GitHub Actions용 최소 권한 IAM 정책 |
| `scripts/create-ecr-repos.sh` | ECR 리포지토리 초기 생성 스크립트 (1회 실행용) |

---

## ☁️ 아키텍처 개요

```
개발자 Push
    │
    ├─ develop 브랜치 ──→ [GitHub Actions] ──→ ECR (short-cut-api-staging)
    │                          │                      └─ 태그: <sha>, staging-latest
    │                          │ OIDC 인증 (키 없음)
    └─ main 브랜치 ────→ [GitHub Actions] ──→ ECR (short-cut-api-prod)
       또는 v* 태그                │                  └─ 태그: <sha>, latest, v*
                                   └─ ECS 서비스 업데이트 (ECS_SERVICE_PROD 설정 후 활성화)
```

---

## 🔐 인증 전략: GitHub Actions OIDC (Zero Static Key)

AWS Access Key를 GitHub Secrets에 저장하지 않습니다.  
GitHub Actions가 발급한 **OIDC JWT 토큰**으로 AWS STS에서 임시 크레덴셜을 발급받아 사용합니다.

### OIDC IAM 역할 수동 설정 가이드 (최초 1회)

**1단계: OIDC Provider 생성**
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**2단계: Trust Policy 파일 생성** (`/tmp/github-trust.json`)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::263636208782:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub":
          "repo:gksshing/SKN22-4th-2Team:ref:refs/heads/*"
      }
    }
  }]
}
```

**3단계: IAM 역할 및 정책 생성**
```bash
# IAM 역할 생성
aws iam create-role \
  --role-name github-actions-ecr-role \
  --assume-role-policy-document file:///tmp/github-trust.json

# 정책 부착 (infra/iam/github-actions-oidc-policy.json 사용)
aws iam put-role-policy \
  --role-name github-actions-ecr-role \
  --policy-name GithubActionsECRPolicy \
  --policy-document file://infra/iam/github-actions-oidc-policy.json
```

---

## 🏷️ 이미지 태깅 전략

| 상황 | 태그 |
|------|------|
| `develop` 브랜치 push | `<sha7>`, `staging-latest` |
| `main` 브랜치 push | `<sha7>`, `latest` |
| `v*` 태그 push | `<sha7>`, `latest`, `v1.2.3` |

- **`<sha7>`**: 커밋 SHA 앞 7자리 – 특정 빌드로 정확한 롤백 가능
- **`staging-latest` / `latest`**: 롤링 태그 – 항상 최신 이미지 참조
- **`v*` 시맨틱 버전**: 릴리즈 이정표 – 운영 호환성 보장

---

## ⚡ 빌드 캐시 최적화 (GitHub Cache API)

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

- `type=gha`: GitHub Actions Cache API 활용 (별도 인프라 없음)
- `mode=max`: 모든 레이어 캐시 저장 – 의존성 미변경 시 빌드 시간 ~70% 단축
- Dockerfile이 `requirements-api.txt`를 소스 코드보다 먼저 COPY하도록 설계되어 있어 패키지 레이어 캐시 적중률 최대화

---

## 🌿 브랜치별 배포 전략

| 브랜치 | ECR 리포지토리 | 용도 | ECS 자동 배포 |
|--------|---------------|------|--------------|
| `develop` | `short-cut-api-staging` | QA/통합 테스트 | ❌ (수동) |
| `main` | `short-cut-api-prod` | 운영 | ✅ (ECS_SERVICE_PROD 설정 후) |
| `v*` 태그 | `short-cut-api-prod` | 릴리즈 | ✅ (ECS_SERVICE_PROD 설정 후) |

---

## 🔧 GitHub Secrets 설정 목록

GitHub Repository → Settings → Secrets and Variables → Actions에 등록:

| Secret 이름 | 값 | 비고 |
|------------|-----|------|
| `AWS_ACCOUNT_ID` | `263636208782` | |
| `AWS_REGION` | `ap-northeast-2` | |
| `ECR_REPO_STAGING` | `short-cut-api-staging` | |
| `ECR_REPO_PROD` | `short-cut-api-prod` | |
| `ECS_CLUSTER_PROD` | `short-cut-cluster` | |
| `ECS_SERVICE_PROD` | (ECS 서비스 생성 후 등록) | **미설정 시 ECS 배포 스텝 자동 스킵** |

---

## 🚀 운영 순서 (Setup Checklist)

- [ ] `scripts/create-ecr-repos.sh` 실행하여 ECR 리포지토리 2개 생성
- [ ] OIDC Provider 생성 (위 가이드 1단계)
- [ ] IAM 역할 `github-actions-ecr-role` 생성 및 정책 부착 (위 가이드 2~3단계)
- [ ] GitHub Secrets 6개 등록 (`ECS_SERVICE_PROD` 제외 5개 먼저 등록)
- [ ] `develop` 브랜치에 더미 push → GitHub Actions 탭에서 워크플로우 실행 확인
- [ ] ECR Console에서 `short-cut-api-staging`에 이미지 확인
- [ ] ECS 클러스터/서비스 생성 (Issue #8 범위) 후 `ECS_SERVICE_PROD` Secret 등록
- [ ] `main` 브랜치 머지 → Production 자동 배포 확인

---

## 📋 PM 에이전트 전달용 상태 업데이트

**Epic: CI/CD 및 보안**
- [x] `.github/workflows/ecr-cicd.yml` 작성 완료
- [x] GitHub Actions OIDC IAM 정책 JSON 생성 (`infra/iam/github-actions-oidc-policy.json`)
- [x] ECR 리포지토리 초기 생성 스크립트 (`scripts/create-ecr-repos.sh`)
- [ ] OIDC IAM 역할 실제 생성 (수동 작업 필요 – 위 가이드 참조)
- [ ] GitHub Secrets 등록 (수동 작업 필요)
- [ ] `ECS_SERVICE_PROD` 등록 후 ECS 자동 배포 활성화 (Issue #8 의존)
