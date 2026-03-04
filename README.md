# 🔍 Short-Cut (쇼특허 AI)

> **AI 기반 특허 침해 선행기술 조사 자동화 서비스**
> 아이디어를 입력하면 AI가 기존 특허와의 중복·침해 리스크를 실시간으로 분석해 드립니다.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black"/>
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?style=for-the-badge&logo=typescript&logoColor=white"/>
  <img src="https://img.shields.io/badge/AWS_ECS-Fargate-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white"/>
  <img src="https://img.shields.io/badge/Pinecone-Vector_DB-00CF86?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white"/>
</p>

---

## 📖 목차

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [RAG 파이프라인](#-rag-파이프라인)
- [프로젝트 구조](#-프로젝트-구조)
- [빠른 시작 (로컬 개발)](#-빠른-시작-로컬-개발)
- [환경 변수 설정](#-환경-변수-설정)
- [API 명세](#-api-명세)
- [배포 (AWS ECS)](#-배포-aws-ecs)
- [팀원 및 역할](#-팀원-및-역할)

---

## 🎯 프로젝트 소개

특허 사전 검토는 기존에 **변리사 수동 검토** 기준 건당 **평균 250만 원**, **수주 이상의 소요 시간**이 필요한 고비용·고시간 프로세스였습니다.

**Short-Cut(쇼특허 AI)** 는 이 비효율을 OpenAI GPT와 RAG(Retrieval-Augmented Generation) 기술로 해결합니다.

| 항목 | 기존 방식 | Short-Cut |
|------|----------|-----------|
| **비용** | 건당 평균 250만 원 | 저비용 AI 분석 |
| **시간** | 수주 이상 | **30초 이내** |
| **접근성** | 전문가 의존 | 누구나 즉시 이용 |

### 주요 타겟 사용자

- 🚀 **창업 준비자 / 발명가** — 아이디어 구상 단계에서 즉각적인 특허성 검토
- 💼 **스타트업** — R&D 초기 IP 리스크 관리 비용의 획기적 절감
- 🏢 **기업 R&D 담당자** — 방대한 특허 문헌에서 유관 특허를 신속하게 필터링

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🔐 **회원 인증** | 이메일 + bcrypt 기반 가입/로그인, JWT 토큰 세션 관리 |
| 💡 **아이디어 분석** | 20~2,000자 텍스트 입력 → SSE 스트리밍 실시간 분석 |
| 📊 **결과 시각화** | 위험도 배지(High/Medium/Low), 유사도 점수 바 차트, 유사 특허 카드 |
| 📜 **히스토리 관리** | 사이드바에서 과거 분석 내역 최신순 조회 및 즉시 재분석 |
| 🛡️ **Rate Limiting** | Redis 기반 일일 10회 제한, 429 응답 + Retry-After 헤더 |
| 📄 **PDF 내보내기** | 분석 결과 PDF 저장 (브라우저 인쇄 기반) |

---

## 🛠️ 기술 스택

| 레이어 | 기술 | 상세 |
|--------|------|------|
| **Frontend** | React 18 + Vite + TypeScript | Tailwind CSS, Lucide React, SSE 스트리밍 |
| **Backend** | FastAPI (Python 3.11+) | Uvicorn ASGI, Pydantic v2, SQLAlchemy + Alembic |
| **AI / RAG** | LangChain + OpenAI API | GPT-4o / GPT-4o-mini 이중 모델 전략, text-embedding-3-small |
| **Vector DB** | Pinecone | Hybrid Search (Dense + BM25), IPC 필터링 |
| **Database** | PostgreSQL (AWS RDS) | SQLAlchemy ORM, Alembic 마이그레이션 |
| **Cache** | Redis | Rate Limit 카운터 영속화 |
| **Infra** | AWS ECS Fargate | ALB, ECR, VPC, CloudWatch |
| **CI/CD** | GitHub Actions | OIDC 인증, Docker 멀티 스테이지 빌드, ECS 롤링 업데이트 |
| **보안** | AWS Secrets Manager | JWT, bcrypt, 프롬프트 인젝션 방어 |

---

## 🏗️ 시스템 아키텍처

```
[사용자 브라우저]
      │
      ├── HTTPS ──▶ [React SPA (Frontend)]
      │                    │
      │                    ├── SSE 스트리밍 ──▶ [FastAPI Backend (ECS Fargate)]
      │                    │                         │
      │                    │              ┌──────────┼──────────┐
      │                    │              ▼          ▼          ▼
      │                    │         [Pinecone]  [RDS/PG]   [Redis]
      │                    │         [OpenAI]   [히스토리]  [Rate Limit]
      │                    │         [Secrets Manager]
      │
      └── ALB (short-cut-api-alb)
              └── ECS Cluster (short-cut-prod-cluster)
```

### AWS 주요 리소스

| 리소스 | 식별자 | 용도 |
|--------|--------|------|
| VPC | `vpc-0f6976edadb541504` | 전체 네트워크 격리 |
| ALB | `short-cut-api-alb` | 트래픽 분산 + 헬스체크 |
| ECS 클러스터 | `short-cut-prod-cluster` | Fargate 컨테이너 실행 |
| RDS | `short-cut-db` (db.t3.micro) | PostgreSQL 15.10 |
| ECR | `short-cut` | Docker 이미지 저장소 |
| Secrets Manager | `short-cut/prod/app` | API 키 및 DB 자격증명 |

---

## 🤖 RAG 파이프라인

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
    └─ OpenAI text-embedding-3-small → 벡터 변환
    │
    ▼
[3] 하이브리드 검색 (vector_db.py)
    ├─ Dense Search: Pinecone 코사인 유사도
    └─ BM25 Sparse Search: 키워드 기반
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
[6] SSE 스트리밍 응답 → 프론트엔드 실시간 표시
```

---

## 📁 프로젝트 구조

```
SKN22-4th-2Team/
├── src/                        # 백엔드 핵심 로직
│   ├── api/                    # FastAPI 라우터 & 서비스
│   │   ├── main.py             # 앱 초기화, CORS 설정
│   │   ├── v1/                 # API v1 엔드포인트
│   │   │   ├── analyze.py      # POST /api/v1/analyze (SSE)
│   │   │   └── history.py      # GET /api/v1/history
│   │   └── services/           # 비즈니스 로직
│   ├── patent_agent.py         # Self-RAG 로직 (HyDE, 멀티쿼리)
│   ├── self_rag_generator.py   # GPT 기반 리포트 생성
│   ├── vector_db.py            # Pinecone Hybrid Search
│   ├── preprocessor.py         # 특허 문서 전처리
│   ├── reranker.py             # Cross-Encoder 재순위화
│   ├── embedder.py             # OpenAI 임베딩
│   ├── rate_limiter.py         # Redis 기반 사용량 제한
│   ├── security.py             # JWT 생성/검증
│   ├── config.py               # 환경변수 & Secrets Manager
│   ├── history_manager.py      # 분석 히스토리 관리
│   └── database/               # SQLAlchemy 모델 & DB 연결
│
├── frontend/                   # React + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx             # 메인 앱 진입점
│   │   ├── components/         # UI 컴포넌트 모음
│   │   ├── hooks/              # 커스텀 훅 (useRagStream 등)
│   │   ├── services/           # API 통신 레이어
│   │   └── types/              # TypeScript 타입 정의
│   └── package.json
│
├── infra/                      # AWS 인프라 설정
│   ├── iam/                    # IAM 정책 정의
│   └── ecs/                    # ECS Task Definition
│
├── tests/                      # 테스트 코드
│   ├── test_evaluation_golden.py   # Golden Dataset 성능 평가
│   ├── test_hybrid_search.py       # 하이브리드 검색 테스트
│   └── test_parser.py              # 파싱 로직 검증
│
├── scripts/                    # 운영 보조 스크립트
├── 01_requirements_spec/       # 요구사항 명세서
├── 02_ui_wireframe/            # UI 와이어프레임
├── 03_system_architecture/     # 시스템 아키텍처 문서
├── 04_test_plan_results/       # 테스트 계획 및 결과
├── Dockerfile                  # 멀티 스테이지 빌드
├── docker-compose.yml          # 로컬 개발용
└── .github/workflows/          # GitHub Actions CI/CD
```

---

## 🚀 빠른 시작 (로컬 개발)

### 사전 요구사항

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### 1. 저장소 클론

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN22-4th-2Team.git
cd SKN22-4th-2Team
```

### 2. 환경 변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성 후 값 입력
cp frontend/.env.example frontend/.env
# 루트 .env 파일 생성 (하단 환경 변수 섹션 참고)
```

### 3. Docker Compose로 실행 (권장)

```bash
# API 서버 + Redis 동시 구동
docker compose up --build

# 로그 확인
docker compose logs -f api
```

서버 실행 후 → **http://localhost:8000** 접속

### 4. 로컬 직접 실행 (개발 모드)

**Backend:**
```bash
pip install -r requirements.txt
APP_ENV=local uvicorn src.api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

프론트엔드 → **http://localhost:5173**

---

## 🔑 환경 변수 설정

`.env` 파일에 아래 변수를 설정하세요. (절대 Git에 커밋하지 마세요)

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | ✅ |
| `PINECONE_API_KEY` | Pinecone API 키 | ✅ |
| `PINECONE_INDEX_NAME` | Pinecone 인덱스명 | ✅ |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | ✅ |
| `REDIS_URL` | Redis 연결 URL | ✅ |
| `JWT_SECRET_KEY` | JWT 서명용 비밀키 | ✅ |
| `JWT_ALGORITHM` | JWT 알고리즘 (기본: HS256) | ✅ |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 토큰 만료 시간 (분) | ✅ |
| `APP_ENV` | 실행 환경 (`local` / `production`) | ✅ |

> **운영 환경**: 모든 시크릿은 **AWS Secrets Manager** (`short-cut/prod/app`)에서 자동 로드됩니다.

---

## 📡 API 명세

| Method | 경로 | 설명 | 인증 |
|--------|------|------|------|
| `POST` | `/api/v1/analyze` | 특허 침해 분석 요청 (SSE 스트리밍) | JWT |
| `GET` | `/api/v1/history` | 사용자 분석 히스토리 조회 | JWT |
| `POST` | `/api/v1/auth/signup` | 회원가입 | 없음 |
| `POST` | `/api/v1/auth/login` | 로그인 (JWT 발급) | 없음 |
| `POST` | `/api/v1/auth/logout` | 로그아웃 | JWT |
| `GET` | `/health` | ALB 헬스체크 | 없음 |

> 전체 API 문서: 서버 실행 후 `http://localhost:8000/docs` (Swagger UI)

---

## ☁️ 배포 (AWS ECS)

CI/CD는 **GitHub Actions**로 자동화되어 있습니다.  
`main` 브랜치에 Push 시 자동 배포가 트리거됩니다.

```
코드 Push (GitHub main)
    │
    ▼
GitHub Actions (.github/workflows/deploy.yml)
    ├─ [1] 코드 체크아웃
    ├─ [2] AWS ECR 로그인 (OIDC)
    ├─ [3] Docker 멀티 스테이지 빌드
    │       ├─ Stage 1: Frontend (Node.js) → /dist 빌드
    │       └─ Stage 2: Backend (Python) → FastAPI 앱
    ├─ [4] ECR Push (SHA + latest 태깅)
    └─ [5] ECS Rolling Update (무중단 배포)
```

---

## 👥 팀원 및 역할

> SKN22 4기 2팀 — 뀨💕

| 역할 | 담당 영역 |
|------|----------|
| **PM / Scrum Master** | 백로그 관리, 칸반 보드, UX 기획 |
| **Backend Engineer** | FastAPI, RAG 파이프라인, DB 설계 |
| **Frontend Engineer** | React UI/UX, API 연동, 상태 관리 |
| **DevOps Engineer** | AWS 인프라, CI/CD, Docker, 보안 |

---

## 📚 관련 문서

- 📋 [요구사항 명세서](./01_requirements_spec/01_requirements_spec.md)
- 🎨 [UI 와이어프레임](./02_ui_wireframe/)
- 🏗️ [시스템 아키텍처](./03_system_architecture/03_system_architecture.md)
- 📂 [파일 구조 가이드](./FILE_STRUCTURE.md)
- ☁️ [AWS CLI 가이드](./devops/AWS_CLI_GUIDE.md)

---

## 📄 라이센스

This project is licensed under the terms specified in the [LICENSE](./LICENSE) file.

---

<p align="center">
  <b>Built with ❤️ by SKN22-4th-2Team</b><br/>
  <i>AI가 모든 발명가의 특허 조사를 지원하는 세상을 만듭니다.</i>
</p>
