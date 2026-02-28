# [2026-02-27] ECR CI/CD 파이프라인 에러 및 Secret 누락 문제 해결 제언

## 주요 문제 사항
최근 `main`에서 `develop` 브랜치로 배포 파이프라인(Production Job)의 트리거를 수정하고 푸시한 뒤, 다음과 같은 에러가 발생했습니다:
1. **에러 내용**: `invalid tag "***.dkr.ecr.***.amazonaws.com/:develop": invalid reference format`
2. **원인 분석**: 
   - `build-and-push-production` Job에서 GitHub Secrets의 `${{ secrets.ECR_REPO_PROD }}` 값을 불러와 Docker 이미지 URL을 조합합니다.
   - 현재 **해당 Secret(`ECR_REPO_PROD`)의 값이 비어있거나 등록되지 않아서**, 레지스트리 주소 끝에 레포지토리 이름이 없이 바로 `:`(태그 구분자)가 붙어서 발생한 에러입니다 (`...com/:develop`).
3. **경고 내용 (Warning)**: `Skip output 'image-uri' since it may contain secret.`
   - AWS Account ID (Secret)가 포함된 `image-uri`를 Job의 `outputs`로 내보내려다 발생한 경고입니다. 다운스트림 Job에서 이를 직접 쓰지 않으므로 `ecr-cicd.yml`에서 해당 output 설정을 지워 문제를 해결했습니다.

## 해결 방법
파이프라인이 정상 작동하게 하려면 GitHub의 **Settings > Secrets and variables > Actions** 경로로 들어가서 다음을 확인/등록해야 합니다.

1. **`ECR_REPO_PROD` 시크릿 등록**
   - ECR에 Production 전용 레포지토리(예: `short-cut-api-prod`)가 생성되어 있다면 해당 이름을 값으로 넣습니다.
2. 만약 **Staging 저장소(`ECR_REPO_STAGING`)를 그대로 재사용**하시려는 거라면, 워크플로우 파일에서 `ECR_REPO="${{ secrets.ECR_REPO_PROD }}"` 부분을 `${{ secrets.ECR_REPO_STAGING }}`으로 변경해야 합니다.

---

### 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: CI/CD 및 인프라 버그 픽스**
  - [ ] GitHub Repository Secrets 확인 및 `ECR_REPO_PROD` 변수 추가
  - [ ] `ECR_REPO_PROD` 생성 전일 경우, AWS ECR에 프로덕션용 레포지토리(`short-cut-api-prod`) 생성 (필요 시)
