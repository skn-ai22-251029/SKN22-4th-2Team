# Secrets Manager 리뷰 피드백 반영 사항

## 1. 🛠️ 코드베이스 분석 결과 (수정 사항 요약)
이전 시크릿 매니저 구현 리뷰(Issue #8)에서 발견된 블로커 및 권장 수정 사항을 소스 코드에 모두 반영 완료했습니다.

- **[Critical] config.py 내 시크릿 주입 이슈 해결**
  `config = PatentGuardConfig()` 인스턴스를 생성한 직후 명시적으로 `update_config_from_env()`를 호출하도록 수정하여, Python 모듈의 로드 순서와 무관하게 AWS Secrets Manager에서 받아온 최신 시크릿 값이 안전하게 초기화 단계에 설정되도록 보장했습니다.
- **[Critical] GCP 임시 자격증명 파일 보안 강화**
  `src/secrets_manager.py`에서 GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 위해 임시 생성되는 JSON 파일의 권한을 생성 직후 `os.chmod(tmp.name, 0o600)`을 적용하여 다른 사용자가 접근하지 못하고 소유자만 읽고 쓸 수 있도록 강화했습니다.
- **[Warning] type hint 일관성 관련 수정**
  `src/secrets_manager.py`의 `dict[str, str]` 타입을 Python 3 모듈 일관성을 위해 `typing.Dict[str, str]`로 깔끔하게 수정했습니다.
- **[Warning] JSON 구조 수정**
  `infra/iam/secret-structure-example.json` 구조를 `{"_comment": ...}` 구조를 포함하는 평평한(flat) 형태로 수정하여 AWS 콘솔이나 AWS CLI 사용 시 혼란을 방지했습니다. (devops 소관이나 프로젝트 완성도를 위해 지원함)
- **오탈자 수정**
  `config.py` 파일 내에 있던 오탈자 "실실", "사각", "홈출" 부분을 의미에 맞게 올바르게 수정했습니다.

## 2. 📋 PM 및 DevOps 전달용 백로그
해당 과제는 에러 수정으로 백로그 처리를 마무리할 수 있는 상태입니다.

- **Epic: RAG 로직 고도화 (Backend)**
  - [x] (완료) Secrets Manager 연동 코드 Critical 결함 2건 수정 완료 (`config.py`, `secrets_manager.py`)
  - [x] (완료) GCP 자격증명 임시 파일 권한 0o600 강제 적용
- **Epic: 컨테이너 및 인프라 구축 (DevOps에게 전달할 사항)**
  - [x] (완료) IAM secret structure JSON 샘플 구조 Flat 형태로 변경
