# 🏗️ Short-Cut (쇼특허 AI) — 시스템 구성도

---

## 1. 전체 시스템 아키텍처

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                                 사용자 (브라우저)                                    │
└─────────────────────────────────────────────┬──────────────────────────────────────┘
                                              │ HTTPS
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                      AWS Cloud (ap-northeast-2, 서울)                               │
│                                                                                    │
│  ┌──────────────────┐    ┌────────────────────────────────────────────────────┐    │
│  │  CloudFront CDN  │    │       VPC (vpc-0f6976edadb541504)                  │    │
│  │  (정적 파일 배포)  │    │       CIDR: 10.0.0.0/16                            │    │
│  └────────┬─────────┘    │                                                    │    │
│           │              │  ┌────────────────────────────────────────────┐    │    │
│           │              │  │         Public Subnet (ALB)                │    │    │
│           │              │  │   ┌─────────────────────────────────────┐  │    │    │
│           └──────────────┼──┼──>│  Application Load Balancer          │  │    │    │
│                          │  │   │  (short-cut-api-alb)                │  │    │    │
│                          │  │   └──────────────┬──────────────────────┘  │    │    │
│                          │  └──────────────────┼─────────────────────────┘    │    │
│                          │                     │                              │    │
│                          │  ┌──────────────────┼─────────────────────────┐    │    │
│                          │  │         Private Subnet                     │    │    │
│                          │  │  ┌──────────────▼───────────────────────┐  │    │    │
│                          │  │  │    ECS Fargate Cluster               │  │    │    │
│                          │  │  │    (short-cut-prod-cluster)          │  │    │    │
│                          │  │  │                                      │  │    │    │
│                          │  │  │  ┌────────────────────────────────┐  │  │    │    │
│                          │  │  │  │  FastAPI Container             │  │  │    │    │
│                          │  │  │  │  (short-cut-api-service)       │  │  │    │    │
│                          │  │  │  │  Port: 8000                    │  │  │    │    │
│                          │  │  │  │                                │  │  │    │    │
│                          │  │  │  │  ├─ RAG Pipeline               │  │  │    │    │
│                          │  │  │  │  ├─ Auth Service               │  │  │    │    │
│                          │  │  │  │  ├─ History API                │  │  │    │    │
│                          │  │  │  │  └─ Rate Limiter               │  │  │    │    │
│                          │  │  │  └────────────────────────────────┘  │  │    │    │
│                          │  │  └──────────────────────────────────────┘  │    │    │
│                          │  │                                            │    │    │
│                          │  │  ┌──────────────────────────────────────┐  │    │    │
│                          │  │  │     RDS PostgreSQL                   │  │    │    │
│                          │  │  │     (short-cut-db)                   │  │    │    │
│                          │  │  │     db.t3.micro / 20GB               │  │    │    │
│                          │  │  │     Private Subnet Only              │  │    │    │
│                          │  │  └──────────────────────────────────────┘  │    │    │
│                          │  └────────────────────────────────────────────┘    │    │
│                          │                                                    │    │
│                          │  ┌────────────────────────────────────────────┐    │    │
│                          │  │           AWS Managed Services             │    │    │
│                          │  │  ┌──────────────────────────────────────┐  │    │    │
│                          │  │  │ AWS Secrets Manager                  │  │    │    │
│                          │  │  │ (short-cut/prod/app)                 │  │    │    │
│                          │  │  │  ├─ OPENAI_API_KEY                   │  │    │    │
│                          │  │  │  ├─ PINECONE_API_KEY                 │  │    │    │
│                          │  │  │  ├─ DATABASE_URL                     │  │    │    │
│                          │  │  │  ├─ REDIS_URL                        │  │    │    │
│                          │  │  │  └─ JWT_SECRET_KEY                   │  │    │    │
│                          │  │  └──────────────────────────────────────┘  │    │    │
│                          │  │  ┌──────────────────┐ ┌─────────────────┐  │    │    │
│                          │  │  │ ECR Repository   │ │ CloudWatch      │  │    │    │
│                          │  │  │ (Docker 이미지)   │ │ Logs + Alarm    │  │    │    │
│                          │  │  └──────────────────┘ └─────────────────┘  │    │    │
│                          │  └────────────────────────────────────────────┘    │    │
│                          └────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────────┘


                외부 SaaS 서비스
                ┌──────────────────────────────────────┐
                │  Pinecone (벡터 DB, us-east-1)        │
                │  OpenAI API (GPT + Embedding)        │
                │  Redis Cloud (Rate Limit 카운터)      │
                └──────────────────────────────────────┘
```

---

## 2. 컴포넌트별 상세 구성

### 2-1. 프론트엔드 (React SPA)

| 항목                 | 내용                                          |
| -------------------- | --------------------------------------------- |
| **프레임워크** | React 18 + Vite + TypeScript                  |
| **스타일**     | Tailwind CSS                                  |
| **배포 방식**  | FastAPI에서 정적 파일 직접 서빙 (`/dist`)   |
| **상태 관리**  | React useState / useContext (라이브러리 없음) |
| **API 통신**   | Fetch API (SSE 스트리밍 포함)                 |

**주요 화면**

| 화면            | 경로              | 설명                                         |
| --------------- | ----------------- | -------------------------------------------- |
| 메인 (분석 전)  | `/`             | IPC 필터 + 아이디어 입력 + 히스토리 사이드바 |
| 분석 진행 중    | `/` (상태 변환) | 스켈레톤 + 프로그레스 바                     |
| 분석 결과       | `/` (상태 변환) | 위험도 배지 + 유사 특허 카드                 |
| 로그인/회원가입 | `/` (오버레이)  | AuthGuard 오버레이 방식                      |

---

### 2-2. 백엔드 (FastAPI)

| 항목                 | 내용                   |
| -------------------- | ---------------------- |
| **프레임워크** | FastAPI (Python 3.11+) |
| **서버**       | Uvicorn (ASGI)         |
| **포트**       | 8000                   |
| **헬스체크**   | `GET /health`        |
| **인증 방식**  | JWT (Bearer Token)     |

**API 라우팅 구조**

```
src/api/
├── main.py            # FastAPI 앱 초기화, 라우터 등록, CORS 설정
├── middleware.py       # 요청 로깅, 에러 핸들링 미들웨어
├── dependencies.py     # 공통 의존성 주입 (DB 세션, 사용자 인증)
├── v1/                 # API 버전 1
│   ├── analyze.py      # POST /api/v1/analyze (SSE 스트리밍)
│   └── history.py      # GET /api/v1/history
├── services/           # 비즈니스 로직
│   ├── auth.py         # 인증/인가 서비스
│   └── rag.py          # RAG 파이프라인 서비스
└── schemas/            # Pydantic 요청/응답 모델
```

**핵심 모듈 구조**

```
src/
├── pipeline.py          # RAG 파이프라인 오케스트레이터
├── vector_db.py         # Pinecone Hybrid Search (Dense + BM25)
├── self_rag_generator.py # OpenAI GPT 기반 리포트 생성
├── rate_limiter.py       # Redis 기반 사용량 제한
├── security.py           # JWT 생성/검증
├── config.py             # 환경변수 로딩 (AWS Secrets Manager)
└── secrets_manager.py    # AWS Secrets Manager 클라이언트
```

---

### 2-3. RAG 파이프라인 흐름

```
사용자 입력 (아이디어 텍스트)
    │
    ▼
[1] 전처리 (preprocessor.py)
    ├─ 프롬프트 인젝션 탐지 및 필터링
    └─ IPC 필터 적용
    │
    ▼
[2] 임베딩 (embedder.py)
    └─ OpenAI text-embedding-3-small→ 벡터 변환
    │
    ▼
[3] 하이브리드 검색 (vector_db.py)
    ├─ Dense Search: Pinecone 코사인 유사도 검색
    └─ BM25 Sparse Search: 키워드 기반 검색
    │
    ▼
[4] 재순위화 (reranker.py)
    └─ Cross-Encoder 기반 결과 재정렬
    │
    ▼
[5] 리포트 생성 (self_rag_generator.py)
    ├─ GPT-4o-mini: 빠른 초기 리포트
    └─ GPT-4o: 심화 분석 (필요시)
    │
    ▼
[6] SSE 스트리밍 응답
    └─ 프론트엔드로 실시간 전송
```

---

### 2-4. 데이터베이스 구성

| 항목                | 내용                                    |
| ------------------- | --------------------------------------- |
| **DB 엔진**   | PostgreSQL 15.10                        |
| **인스턴스**  | `short-cut-db` (db.t3.micro)          |
| **스토리지**  | 20GB gp2                                |
| **접근 방식** | 프라이빗 서브넷 전용 (퍼블릭 접근 차단) |
| **ORM**       | SQLAlchemy + Alembic (마이그레이션)     |
| **백업**      | 7일 보존                                |

**테이블 구조**

```
┌─────────────────┐         ┌──────────────────────────┐
│     users       │         │    analysis_history      │
├─────────────────┤         ├──────────────────────────┤
│ id (UUID, PK)   │<────────│ user_id (UUID, FK)       │
│ email (UNIQUE)  │         │ id (UUID, PK)            │
│ hashed_password │         │ session_id (VARCHAR)     │
│ created_at      │         │ idea (TEXT)              │
└─────────────────┘         │ risk_level (ENUM)        │
                            │ risk_score (FLOAT)       │
                            │ similar_count (INT)      │
                            │ result_json (JSONB)      │
                            │ created_at (TIMESTAMP)   │
                            └──────────────────────────┘
```

---

### 2-5. AWS 인프라 리소스 목록

| 리소스                      | 식별자                                         | 용도                               |
| --------------------------- | ---------------------------------------------- | ---------------------------------- |
| **VPC**               | `vpc-0f6976edadb541504`                      | 전체 네트워크 격리 공간            |
| **퍼블릭 서브넷**     | (ALB 위치)                                     | 인터넷 트래픽 수신                 |
| **프라이빗 서브넷 A** | `subnet-05bb7a36fc8652479` (ap-northeast-2a) | ECS + RDS                          |
| **프라이빗 서브넷 B** | `subnet-08d45e802f3e89cbe` (ap-northeast-2b) | ECS + RDS                          |
| **ALB**               | `short-cut-api-alb`                          | 트래픽 분산 + 헬스체크             |
| **ECS 클러스터**      | `short-cut-prod-cluster`                     | Fargate 컨테이너 실행              |
| **ECS 서비스**        | `short-cut-api-service-alb`                  | FastAPI 서비스                     |
| **ECS SG**            | `sg-0806d76177a2c0e37`                       | ECS 보안 그룹                      |
| **RDS 인스턴스**      | `short-cut-db`                               | PostgreSQL DB                      |
| **RDS SG**            | `sg-0ce9a0c8aa5f38c42`                       | RDS 보안 그룹 (ECS → 5432만 허용) |
| **ECR**               | `short-cut` (Repository)                     | Docker 이미지 저장소               |
| **Secrets Manager**   | `short-cut/prod/app`                         | API 키 및 DB 자격증명              |
| **CloudWatch**        | Logs + Alarm                                   | 로그 수집 및 알람                  |

---

### 2-6. 보안 그룹 규칙

```
인터넷
  │ 443 (HTTPS)
  ▼
ALB SG
  │ 8000 (HTTP)
  ▼
ECS SG (sg-0806d76177a2c0e37)
  │ 5432 (PostgreSQL)
  ▼
RDS SG (sg-0ce9a0c8aa5f38c42)
  └─ 인바운드: ECS SG에서만 허용
  └─ 퍼블릭 액세스: 차단
```

---

### 2-7. CI/CD 파이프라인

```
개발자 Push (GitHub)
    │
    ▼
GitHub Actions (./github/workflows/deploy.yml)
    │
    ├─ [1] 코드 체크아웃
    ├─ [2] AWS ECR 로그인 (OIDC, Long-term Key 없음)
    ├─ [3] Docker 멀티 스테이지 빌드
    │       ├─ Stage 1: Frontend (Node.js) → /dist 빌드
    │       └─ Stage 2: Backend (Python) → FastAPI 앱
    ├─ [4] ECR Push (이미지 태깅: SHA + latest)
    └─ [5] ECS Rolling Update (무중단 배포)
```

---

### 2-8. 외부 서비스 연동

| 서비스                | 리전/위치 | 용도                     | 연동 방식           |
| --------------------- | --------- | ------------------------ | ------------------- |
| **OpenAI API**  | 글로벌    | GPT 리포트 생성 + 임베딩 | REST API            |
| **Pinecone**    | us-east-1 | 특허 벡터 검색           | Pinecone Python SDK |
| **Redis Cloud** | 외부 SaaS | Rate Limit 카운터        | Redis 클라이언트    |

---

## 3. 데이터 흐름 요약

```
┌───────┐    아이디어 텍스트     ┌──────────┐    벡터 쿼리     ┌──────────┐
│ 사용자 │  ────────────────>   │ FastAPI  │ ────────────>  │ Pinecone │
│       │                      │ (ECS)    │ <────────────  │ (벡터DB)  │
│       │  <────────────────   │          │  유사 특허 결과  └──────────┘
└───────┘     SSE 스트리밍      │          │
                               │          │    GPT 호출     ┌──────────┐
                               │          │ ─────────────> │  OpenAI  │
                               │          │ <───────────── │    API   │
                               │          │ 리포트 스트리밍   └──────────┘
                               │          │
                               │          │   사용량 확인     ┌──────────┐
                               │          │ ─────────────>  │  Redis   │
                               │          │ <────────────── └──────────┘
                               │          │
                               │          │   히스토리 저장   ┌──────────┐
                               │          │ ─────────────>  │ RDS(PG)  │
                               └──────────┘                 └──────────┘
```

---

## 4. 환경 변수 목록 (Secrets Manager: `short-cut/prod/app`)

| 키                                  | 용도                        |
| ----------------------------------- | --------------------------- |
| `OPENAI_API_KEY`                  | OpenAI GPT + Embedding 호출 |
| `PINECONE_API_KEY`                | Pinecone 벡터 DB 접근       |
| `PINECONE_INDEX_NAME`             | 검색 대상 인덱스명          |
| `DATABASE_URL`                    | PostgreSQL 연결 문자열      |
| `REDIS_URL`                       | Redis Rate Limiter 연결     |
| `JWT_SECRET_KEY`                  | JWT 토큰 서명 키            |
| `JWT_ALGORITHM`                   | JWT 알고리즘 (HS256)        |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 토큰 만료 시간              |
