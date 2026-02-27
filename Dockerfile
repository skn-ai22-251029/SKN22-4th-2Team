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

# ── 비밀 정보 주입 없이 환경 변수 기본값 구성 ─────────────────────────────
# 실제 값은 런타임에 외부(Docker run -e, K8s Secret 등)에서 주입합니다.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH"

# 빌더 스테이지에서 생성한 가상환경만 복사 (컴파일러 제외)
COPY --from=builder /install /install

WORKDIR /app

# 애플리케이션 소스 복사
# .dockerignore에 의해 불필요한 파일은 빌드 컨텍스트에서 이미 제외됩니다.
# src/ 를 먼저 COPY 하면 main.py만 수정 시 src/ 레이어 캐시를 재사용합니다.
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY main.py .

# ── entrypoint 스크립트 복사 및 실행 권한 설정 ────────────────────────────
# root 단계에서 복사하여 실행 권한(+x)을 부여합니다.
# 시크릿 로드는 Python bootstrap_secrets()가 처리하며,
# 이 스크립트는 컨테이너 시작 시 필수 환경 변수를 사전 검증합니다.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ── 런타임에 필요한 쓰기 가능 디렉토리 미리 생성 ────────────────────────
# history_manager.py → /app/src/data/history.db
# config.py LoggingConfig → /app/src/logs/
# secrets_manager.py tempfile → /tmp (기본 경로, 별도 생성 불필요)
RUN mkdir -p /app/src/data /app/src/logs

# ── non-root 사용자 생성 및 권한 설정 (최소 권한 원칙) ───────────────────
# - 홈 디렉토리(/home/appuser) 생성: tempfile 등이 홈 디렉토리를 탐색하므로 필수
# - UID=1001 appuser로 실행, 쓰기 필요 경로에만 권한 부여
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup \
    --home /home/appuser --create-home \
    --shell /bin/false appuser \
    && chown -R appuser:appgroup /app /home/appuser

USER appuser

# FastAPI 기본 포트
EXPOSE 8000

# 상태 점검 엔드포인트 활용
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 앱 실행: entrypoint.sh가 환경 변수 검증 후 uvicorn을 호출합니다.
# 실제 시크릿 로드는 Python bootstrap_secrets()에서 처리됩니다.
ENTRYPOINT ["/entrypoint.sh"]
