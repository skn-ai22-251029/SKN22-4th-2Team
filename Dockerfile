# =============================================================================
# 쇼특허 (Short-Cut) – FastAPI Backend Dockerfile
# 멀티 스테이지 빌드 | non-root 실행 | 이미지 최소화
# =============================================================================

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
# slim 이미지를 베이스로 사용해 컴파일 의존성을 빌드 스테이지에만 격리합니다.
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 전용 OS 패키지 설치 (gcc 등 네이티브 확장 빌드 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일만 먼저 복사 → 캐시 레이어 활용
COPY requirements-api.txt .

# pip 업그레이드를 좁 설치와 분리하여 requirements 안 소스가 변경되지 않으면 이 레이어를 재사용합니다.
# pip 버전을 고정하여 업그레이드 버전 혁으로 인한 레이어 다시 빌드 방지
RUN python -m venv /install
RUN /install/bin/pip install --no-cache-dir --upgrade "pip==24.0"
RUN /install/bin/pip install --no-cache-dir -r requirements-api.txt


# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
# 컴파일러 및 빌드 도구 없이 순수 런타임 환경만 구성합니다.
FROM python:3.11-slim AS runtime

# 런타임 OS 패키지 (언어 모델 로딩에 필요한 공유 라이브러리 최소 설치)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── 런타임 환경 설정 및 NLP 모델 사전 다운로드 ─────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    NLTK_DATA=/usr/local/share/nltk_data

# 빌더 스테이지에서 생성한 가상환경만 복사 (컴파일러 제외)
COPY --from=builder /install /install

WORKDIR /app

# NLP 모델 사전 다운로드 (런타임 PermissionError 방지 및 기동 속도 최적화)
RUN mkdir -p ${NLTK_DATA} \
    && python -m nltk.downloader -d ${NLTK_DATA} punkt_tab \
    && python -m spacy download en_core_web_sm

# 애플리케이션 소스 복사
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY main.py .

# ── entrypoint 스크립트 복사 및 실행 권한 설정 ────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ── non-root 사용자 생성 및 권한 설정 (최소 권한 원칙) ───────────────────
# --create-home을 추가하여 /home/appuser를 생성하고, 필요한 경로에 대한 소유권을 부여합니다.
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --create-home --shell /bin/false appuser \
    && chown -R appuser:appgroup /app ${NLTK_DATA} /home/appuser

USER appuser

# FastAPI 기본 포트
EXPOSE 8000

# 상태 점검 엔드포인트 활용
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 앱 실행: entrypoint.sh가 환경 변수 검증 후 uvicorn을 호출합니다.
# 실제 시크릿 로드는 Python bootstrap_secrets()에서 처리됩니다.
ENTRYPOINT ["/entrypoint.sh"]
