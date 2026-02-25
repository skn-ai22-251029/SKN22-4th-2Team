# 🔍 수석 아키텍트 코드 리뷰 #3 — AWS Secrets Manager 시크릿 주입 구조
**리뷰 대상**: Issue #8 Secrets Manager 코드 구현 + DevOps IAM/시크릿 가이드  
**리뷰 일자**: 2026-02-25  
**리뷰어**: Chief Architect / DevSecOps  
**대상 파일**:

| 구분 | 파일 |
|------|------|
| Backend 신규 | `src/secrets_manager.py`, `entrypoint.sh`, `tests/test_secrets_manager.py` |
| Backend 수정 | `src/config.py`, `Dockerfile`, `requirements-api.txt` |
| DevOps 신규 | `docker-compose.yml`, `infra/iam/secrets-read-policy.json`, `infra/iam/ecs-task-trust-policy.json`, `infra/iam/secret-structure-example.json` |
| DevOps 가이드 | `devops/01_secrets_manager_and_iam_setup.md` |

---

### 🔍 총평 (Architecture Review)

로컬(.env) ↔ 프로덕션(Secrets Manager) 이중 구조 설계가 매우 깔끔하며, `bootstrap_secrets()`를 `config.py` 모듈 최상단에서 호출해 `import config` 시점에 즉시 주입되는 구조는 기존 코드와의 하위 호환성을 보장하는 훌륭한 설계다. IAM 정책의 최소 권한(GetSecretValue + DescribeSecret만 허용) + KMS Condition 제한도 잘 적용되었다. 다만, **`config.py`에서 `bootstrap_secrets()` 호출 후 `update_config_from_env()`가 자동 호출되지 않는 문제**, **GCP 임시 파일의 보안 권한 미설정**, **entrypoint.sh의 Windows→Linux CRLF 위험** 등 수정이 필요한 항목이 있다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)

*(아래 내용을 복사해서 Backend / DevOps 에이전트에게 전달하세요)*

---

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `src/config.py:19-20` → **`bootstrap_secrets()` 호출 후 `update_config_from_env()` 미호출**  
  현재 `config.py` 상단에서 `bootstrap_secrets()`를 호출하여 `os.environ`에 시크릿이 주입되지만, 그 **직후에 `update_config_from_env()`가 호출되지 않는다.** `config.py:328`에서 `config = PatentGuardConfig()`가 생성될 때 `os.environ`에서 값을 읽지만, `bootstrap_secrets()`가 먼저 호출되므로 타이밍상 OK로 보인다. **그러나** `dataclass`의 `default_factory`가 아닌 `default` 값(`os.environ.get(...)`)은 **클래스 정의 시점**에 평가되므로, **Python 모듈 로드 순서에 따라 `bootstrap_secrets()` → `config` 인스턴스 생성 순서가 보장되지 않을 수 있다.**  
  → **안전을 위해 `config = PatentGuardConfig()` 생성 직후에 `update_config_from_env()`를 명시적으로 호출하세요.** 이렇게 하면 어떤 import 순서에서도 Secrets Manager 값이 config에 반영됩니다.
  ```python
  # src/config.py 하단 수정
  config = PatentGuardConfig()
  update_config_from_env()  # ← 추가: SM 주입 후 config 동기화 보장
  ```

- `src/secrets_manager.py:154-163` → **GCP 자격증명 임시 파일에 파일 권한(mode) 미설정**  
  `NamedTemporaryFile`로 생성된 임시 파일이 기본 umask(보통 `0o644`)로 생성되어 **다른 사용자가 GCP 서비스 계정 키를 읽을 수 있다.** 컨테이너 내에서는 단일 사용자(`appuser`)이므로 위험도가 낮지만, 로컬 개발 환경에서는 심각한 보안 문제다.  
  → 파일 생성 후 즉시 `os.chmod(tmp.name, 0o600)`으로 소유자만 읽기/쓰기 가능하도록 제한하세요.
  ```python
  tmp.close()
  os.chmod(tmp.name, 0o600)  # ← 추가: 소유자만 접근 가능
  os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
  ```

---

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `entrypoint.sh` → **Windows에서 작성된 파일 — CRLF(\\r\\n) 라인 엔딩 위험**  
  `backend/04_secrets_manager.md:45`에도 명시되었듯이, Windows 환경에서 생성된 쉘 스크립트는 `\r\n` 줄 바꿈이 포함될 수 있다. Linux 컨테이너에서 `#!/bin/sh\r`로 해석되면 **`/bin/sh\r: not found`** 오류가 발생한다. 현재 파일 확인 결과 LF로 되어 있지만(**Good**), `.gitattributes`에 쉘 스크립트의 LF 강제 규칙이 없으므로 다른 기여자가 편집할 때 CRLF로 변경될 수 있다.  
  → `.gitattributes` 파일에 `*.sh text eol=lf`를 추가하여 항상 LF 라인 엔딩을 강제하세요.

- `infra/iam/secrets-read-policy.json:11,20` → **KMS Resource ARN에 `*`(와일드카드) 사용**  
  `devops/01_secrets_manager_and_iam_setup.md`에서도 이미 인지하고 있지만, `arn:aws:kms:us-east-1:*:key/*`는 **모든 AWS 계정의 모든 KMS 키에 대한 Decrypt 권한**을 부여한다. `Condition`의 `ViaService`가 Secrets Manager로 제한하고 있어 실질적 위험은 낮지만, 프로덕션 강화 시 AWS Account ID를 고정해야 한다.  
  → DevOps 가이드 섹션 2-4에 이미 기술됨. 실제 배포 전 반드시 Account ID 교체 필요.

- `infra/iam/secret-structure-example.json:2` → **JSON 최상위 키가 시크릿 이름과 설명이 포함된 비표준 구조**  
  현재 JSON이 `{"short-cut/prod/app 시크릿 구조 예시 (JSON)": {...실제값...}}` 형태로 래핑되어 있다. 이 상태로 Secrets Manager에 등록하면 `_load_from_secrets_manager()` → `json.loads()` 후 최상위 키가 시크릿 이름이 되어 예상과 다르게 파싱된다.  
  → 실제 등록할 JSON은 최상위가 바로 `{"OPENAI_API_KEY": "...", ...}` 형태여야 한다. 이 파일은 **콘솔 참조용 예시**라는 점을 주석이나 README에 더 명확히 명시하거나, 실제 등록 가능한 flat JSON으로 수정하세요.
  ```json
  {
      "_comment": "short-cut/prod/app 시크릿 구조 예시 – 이 파일을 직접 등록하지 마세요",
      "OPENAI_API_KEY": "sk-...",
      "PINECONE_API_KEY": "pcsk_...",
      ...
  }
  ```

- `src/config.py:17` → **주석 오탈자: `"실실 환경"` → `"실행 환경"`, `"사각 주입"` → `"시크릿 주입"`**  
  기능에는 영향 없으나 팀 문서 품질을 위해 수정 권장.

- `src/config.py:338` → **주석 오탈자: `"홈출"` → `"호출"`**  
  `bootstrap_secrets() 홈출 이후에 호출해야 합니다` → `호출 이후에`

- `tests/test_secrets_manager.py` → **테스트 간 모듈 상태 격리 미흡**  
  여러 테스트 클래스에서 `from src.secrets_manager import bootstrap_secrets`를 반복 호출하지만, Python의 모듈 캐싱(`sys.modules`)으로 인해 **이전 테스트의 mock이 다음 테스트에 잔류**할 수 있다. 특히 `setUp()`에서 `os.environ`만 초기화하고 모듈 자체는 리로드하지 않는다.  
  → 각 테스트에서 `importlib.reload(src.secrets_manager)` 호출을 고려하거나, 함수 레벨의 patch scope가 정확한지 재확인하세요.

---

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `src/secrets_manager.py:31,85` → **`dict[str, str]` 타입 힌트 — Python 3.9+ 전용**  
  `from __future__ import annotations`를 사용하므로 문법상 문제는 없지만, `Dict[str, str]` (typing 모듈)과 혼용하면 코드 일관성이 떨어진다. 프로젝트 전체에서 하나로 통일 권장.

- `docker-compose.yml:28` → **볼륨 마운트 `./src:/app/src:ro`가 개발 편의성을 높이지만, 파일 소유권(UID) 불일치 가능**  
  호스트(Windows)와 컨테이너(`appuser:1001`) 간 UID 불일치로 파일 접근 문제가 발생할 수 있다. Docker Desktop for Windows에서는 보통 자동 변환되지만, 알아두면 좋다.

- `Dockerfile:58-59` → **`COPY entrypoint.sh` + `chmod +x` 패턴이 올바르게 non-root 전환 전에 배치됨** → ✅ Good  
  `USER appuser` 이전에 root 권한으로 `chmod +x`를 실행하므로 정상 동작.

- `devops/01_secrets_manager_and_iam_setup.md` → **전체적으로 매우 상세하고 잘 작성된 운영 가이드.**  
  시크릿 등록, IAM 역할 생성, ECS 연동, 로테이션 전략, 트러블슈팅까지 포괄적으로 기술. 보안 체크리스트도 포함되어 DevOps 팀이 바로 실행 가능한 수준. ✅

---

### 💡 Tech Lead의 머지(Merge) 권고

- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **Critical 항목이 수정되기 전까지 머지를 보류하세요.**

> **필수 수정 항목 요약 (머지 전 Blocker)**:
> 1. `src/config.py` — `config = PatentGuardConfig()` 직후에 `update_config_from_env()` 명시적 호출 추가
> 2. `src/secrets_manager.py` — GCP 임시 파일에 `os.chmod(tmp.name, 0o600)` 파일 권한 설정 추가
>
> **권장 수정 (논블로킹, 다음 커밋에서 처리 가능)**:
> - `.gitattributes`에 `*.sh text eol=lf` 추가
> - `infra/iam/secret-structure-example.json` flat JSON 구조로 수정
> - `src/config.py` 주석 오탈자 2건 정리
