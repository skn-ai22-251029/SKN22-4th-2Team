# 12. AWS 리전 / URL 불일치 수정 및 ECS 배포 방해 요소 점검

> **작업일시**: 2026-03-03 16:00 KST  
> **작업자**: Backend AI Engineer  
> **분류**: 배포 준비 / 버그 수정

---

## 🔧 수정 완료 항목

### 1. `src/secrets_manager.py` — AWS Secrets Manager 폴백 리전 수정
- **문제**: `bootstrap_secrets()` 함수의 폴백 리전이 `us-east-1`로 하드코딩
- **영향**: ECS Task Definition에서 `AWS_REGION` 환경변수 주입이 누락될 경우, Secrets Manager 호출이 **버지니아(us-east-1)** 로 날아가면서 시크릿 로드 실패
- **수정**: 폴백 리전을 `ap-northeast-2` (서울) 로 변경
```diff
- region = aws_region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
+ region = aws_region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-2"
```

### 2. `infra/ecs/task-definition-template.json` — ECR 이미지 URL 리전 수정
- **문제**: ECR 이미지 URL에 `us-east-1`이 하드코딩되어 있어 서울 리전 ECR 리포지토리와 불일치
- **영향**: ECS가 이미지를 pull할 때 잘못된 리전의 ECR을 참조하여 **이미지 pull 실패** → 태스크 시작 불가
- **수정**: `ap-northeast-2` 로 변경
```diff
- "image": "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/short-cut-api:latest"
+ "image": "<AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/short-cut-api:latest"
```

---

## ✅ 확인 완료 · 수정 불필요 항목

### 프론트엔드 URL (문제 없음)
| 파일 | 내용 | 판정 |
|------|------|------|
| `frontend/src/utils/apiClient.ts` | `VITE_API_BASE_URL` 환경변수 → 없으면 상대 경로(`''`) 사용 | ✅ 프로덕션 안전 |
| `frontend/vite.config.ts` | proxy `http://localhost:8000` | ✅ 개발 전용 (빌드에 포함 안 됨) |

### 백엔드 URL / CORS (문제 없음)
| 파일 | 내용 | 판정 |
|------|------|------|
| `src/api/main.py` | CORS `ALLOWED_ORIGINS` 환경변수 동적 주입 | ✅ 프로덕션 안전 |
| `src/config.py` L380 | `frontend_url` 기본값 `http://localhost:5173` → `FRONTEND_URL` 환경변수로 재정의 가능 | ✅ OK |
| `Dockerfile` L136 | HEALTHCHECK `localhost:8000` | ✅ 컨테이너 내부 호출이므로 OK |
| `docker-compose.yml` L34 | healthcheck `localhost:8000` | ✅ 컨테이너 내부 호출이므로 OK |

### Pinecone 리전 (수정 불가)
| 파일 | 내용 | 판정 |
|------|------|------|
| `src/config.py` L187 | `region: str = "us-east-1"` | ⚠️ **Pinecone Serverless** 인덱스 리전이며 AWS 리전과는 별개. 변경하면 인덱스 접근 불가. 수정 불필요 |

---

## 🚨 ECS 배포 시 추가 주의사항 (DevOps 전달)

### 1. `app.py` (레거시 Streamlit 앱)
- 루트에 `app.py`가 남아있지만 **ECS 배포 시에는 FastAPI(`src/api/main.py`)만 실행**됨
- `entrypoint.sh`가 `uvicorn src.api.main:app`을 호출하므로 `app.py`는 배포에 영향 없음
- 단, 불필요한 혼동을 막기 위해 향후 정리 권장

### 2. `.env` 파일 의존성
- `docker-compose.yml`이 `.env` 파일을 참조 (`env_file: .env`)
- **ECS 배포 시에는 `.env` 파일이 없으므로** Secrets Manager를 통해 시크릿이 주입되어야 함
- `bootstrap_secrets()`가 이를 처리하지만, 필수 키(OPENAI_API_KEY, PINECONE_API_KEY, JWT_SECRET_KEY)가 Secrets Manager에 등록되어 있는지 사전 확인 필요

### 3. `FRONTEND_URL` 환경변수
- ECS Task Definition에 `FRONTEND_URL` 환경변수가 미설정 시 `http://localhost:5173`으로 폴백
- 실제 운영 도메인으로 설정해야 CORS/리다이렉트가 정상 동작함
- Task Definition의 `environment` 배열에 추가 필요

### 4. 테스트용 `.py` 파일들
- 루트에 `tmp_test_*.py`, `test_bcrypt.py`, `check_*.py` 등 임시/디버그 파일이 다수 존재
- `.dockerignore`로 빌드 시 제외되지만, GitHub 리포지토리 정리 권장

---

## 📋 PM / DevOps 전달용 요약

- **Epic: 배포 블로커 수정 (Backend) — ✅ 완료**
  - [x] `secrets_manager.py` AWS 리전 폴백 `us-east-1` → `ap-northeast-2` 수정
  - [x] `task-definition-template.json` ECR 이미지 URL 리전 수정

- **Epic: 배포 전 확인 (DevOps에게 전달)**
  - [ ] AWS Secrets Manager `short-cut/prod/app` 시크릿에 필수 키 등록 확인 (OPENAI_API_KEY, PINECONE_API_KEY, JWT_SECRET_KEY, DATABASE_URL)
  - [ ] ECS Task Definition에 `FRONTEND_URL` 환경변수 추가 (운영 도메인)
  - [ ] `<AWS_ACCOUNT_ID>` 플레이스홀더를 실제 AWS 계정 ID로 교체
