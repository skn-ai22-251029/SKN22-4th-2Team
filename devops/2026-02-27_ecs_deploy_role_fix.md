# [2026-02-27] ECS 배포 에러(Role is not valid) 해결 제언

## 주요 문제 사항
최근 Production 이미지 빌드/푸시 작업은 성공하였으나, 이후 실행된 `ECS 서비스 업데이트 (Production)` 부분에서 다음과 같은 에러가 발생했습니다:
1. **에러 내용**: `Failed to register task definition in ECS: Role is not valid`
2. **원인 분석**:
   - `aws-actions/amazon-ecs-render-task-definition` Action은 JSON 파일에서 *이미지 주소(image)* 문자열만 찾아서 교체해 줄 뿐, 별도의 환경 변수 치환 작업(예방 치환)을 거치지 않습니다.
   - 프로젝트의 `infra/ecs/task-definition-template.json` 파일 안에는 보안을 위해 ARN 문자열 등에 **`<AWS_ACCOUNT_ID>`** 라는 플레이스홀더를 담아 두셨습니다. 
   - 그러나 이 문자열이 파이프라인 상에서 실제 AWS 계정 ID 치환처리를 거치지 않고 그대로 AWS ECS API로 넘어가다보니, 문자열 형태가 잘못되어 `Role is not valid` 에러가 발생한 것입니다.

## 해결 방법
이를 해결하기 위해 `ecr-cicd.yml` 워크플로우에 `sed` 명령어를 활용하여 템플릿 파일 내부에 있는 `<AWS_ACCOUNT_ID>` 텍스트를 GitHub Secrets에 등록된 실제 Account ID로 사전에 덮어쓰기 하는 스텝(Step)을 추가했습니다.

**[수정된 파이프라인 동작 방식]**
1. 소스 코드 체크아웃 (task-defintion 파일 로드)
2. **✅ (추가된 스텝) `Task Definition 내 AWS Account ID 동적 치환`** 
   - `sed` 명령어로 파일 안의 플레이스홀더를 `${{ secrets.AWS_ACCOUNT_ID }}` 값으로 안전하게 치환
3. ECS Task Definition 이미지 URI 업데이트 플러그인 수행
4. 완료 후 정상 반영!

이제 이 변경사항(수정된 `ecr-cicd.yml`)을 커밋하고 한 번만 더 `develop` 브랜치에 푸시해 주시면, ECS 쪽에도 정상적으로 Task Definition 리비전이 등록되어 배포가 완료될 것입니다!

---

### 📋 PM 에이전트 전달용 기술 백로그 (복사해서 PM에게 전달하세요)
- **Epic: CI/CD 및 인프라 버그 픽스**
  - [x] ECS 배포 파이프라인에서 Task-Definition JSON 파일 내 IAM Role ARN의 Account ID 플레이스홀더 동적 치환(`sed`) 스텝 추가 반영 완료
