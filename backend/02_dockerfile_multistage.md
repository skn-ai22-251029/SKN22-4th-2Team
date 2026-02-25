# [Dockerfile] 멀티 스테이지 빌드 및 최소 권한 사용자 설정

## 1. 완료한 작업 내역
- `requirements-api.txt` 작성: 기존 `requirements.txt`에서 Streamlit / 테스트(pytest, deepeval) / BigQuery 등 API 서버에 불필요한 패키지를 제거하고 FastAPI 서버 전용 최소 의존성만 정리
- `.dockerignore` 작성: `.env`, `.git`, `__pycache__`, `tests/`, `src/data/`, `app.py` 등 컨테이너 빌드 컨텍스트에서 제외하여 보안 강화 및 빌드 속도 개선  
- `Dockerfile` (멀티 스테이지) 작성:
  - **Stage 1 (builder)**: `python:3.11-slim` 기반, `requirements-api.txt` 설치를 `/install` 가상환경에 격리
  - **Stage 2 (runtime)**: 컴파일러 없이 가상환경만 복사 → 불필요한 빌드 도구 미포함으로 이미지 크기 최소화
  - `appuser` (UID 1001, non-root)로 실행 → 최소 권한 원칙 준수
  - `HEALTHCHECK`: `/health` 엔드포인트 주기적 점검 설정
  - `--no-cache-dir` pypi 캐시 미생성으로 레이어 크기 축소

## 2. 다음 단계 권장 사항 (DevOps 전달)
- `docker build -t short-cut-api .` 로컬 빌드 및 이미지 크기 측정 (`docker image inspect`)
- `docker run --env-file .env -p 8000:8000 short-cut-api` 로컬 구동 검증
- 목표 이미지 크기 200MB 이하 달성 여부 확인; 초과 시 `--no-binary` 또는 `multi-arch` 전략 검토

## 3. PM 에이전트 상태 업데이트 요약
- **Issue #6 [멀티 스테이지 Dockerfile 작성]** 초안 완료 (`Dockerfile`, `.dockerignore`, `requirements-api.txt` 생성)
- DevOps 에이전트에게 빌드 검증 및 ECR 푸시 파이프라인 연동 요청 단계로 이관합니다.
