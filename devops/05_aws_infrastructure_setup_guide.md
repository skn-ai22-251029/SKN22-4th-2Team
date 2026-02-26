# 🔐 AWS 인프라 연동 및 GitHub Secrets 설정 가이드

**AWS OIDC Provider 및 ECR 리포지토리가 생성되었습니다.** 
이제 GitHub Actions에서 이 리소스들에 접근할 수 있도록 환경 변수(Secrets)를 설정해야 합니다.

## ✅ 등록해야 할 GitHub Secrets 목록

GitHub 저장소의 **[Settings] -> [Secrets and variables] -> [Actions] -> [New repository secret]** 메뉴로 이동하여 다음 4개의 값을 등록해 주세요.

| Secret Name | 입력할 값 |
| :--- | :--- |
| `AWS_ACCOUNT_ID` | `283636208782` |
| `AWS_REGION` | `ap-northeast-2` |
| `ECR_REPO_STAGING` | `short-cut-api-staging` |
| `ECR_REPO_PROD` | `short-cut-api-prod` |

---

### 💡 (참고) 각 Secret의 역할

1. **`AWS_ACCOUNT_ID`**: GitHub Actions OIDC 인증 과정에서 AWS 계정을 식별하고, `arn:aws:iam::283636208782:role/github-actions-oidc-role`에 접근하기 위해 사용됩니다.
2. **`AWS_REGION`**: ECR 및 ECS 리소스가 위치한 AWS 리전을 지정합니다 (서울 리전의 경우 `ap-northeast-2`).
3. **`ECR_REPO_*`**: Docker 이미지를 푸시할 저장소의 이름을 지정합니다. 하드코딩을 방지하고 환경별(Staging/Prod) 유연성을 제공합니다.

> [!IMPORTANT]
> 위 4개의 Secret이 모두 올바르게 등록되어야 `.github/workflows/ecr-cicd.yml`의 OIDC 인증 및 Docker 이미지 푸시가 정상적으로 작동합니다.
> Secret 등록을 마치신 후, 저에게 알려주시면 **파이프라인 빌드 및 푸시 테스트(Staging 환경)**를 진행하겠습니다.
