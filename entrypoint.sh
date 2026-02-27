#!/bin/sh
# =============================================================================
# 쇼특허(Short-Cut) – 컨테이너 엔트리포인트
# =============================================================================
# 역할:
#   1. 프로덕션 환경에서 필수 AWS 환경 변수 존재 여부 사전 검증
#   2. uvicorn으로 FastAPI 앱 실행 (시크릿 주입은 Python bootstrap_secrets가 처리)
#
# 주의:
#   실제 시크릿 로드(AWS Secrets Manager 호출)는 Python 앱 내부
#   src/secrets_manager.bootstrap_secrets()에서 처리됩니다.
#   이 스크립트는 컨테이너 레이어에서 빠른 실패(fail-fast)를 보장합니다.
# =============================================================================

set -e

echo "[entrypoint] APP_ENV=${APP_ENV:-local} 환경으로 시작합니다."

# ── 프로덕션 전용 필수 환경 변수 검증 ─────────────────────────────────────
if [ "${APP_ENV}" = "production" ]; then
    # AWS_REGION이 없으면 즉시 오류 출력 후 종료
    : "${AWS_REGION:?[entrypoint] 오류: AWS_REGION 환경 변수가 설정되지 않았습니다.}"
    # SECRET_NAME이 없으면 기본값으로 폴백 (Python 쪽 기본값과 동기)
    export SECRET_NAME="${SECRET_NAME:-short-cut/prod/app}"
    echo "[entrypoint] Secrets Manager 시크릿: ${SECRET_NAME} (region: ${AWS_REGION})"
fi

# ── uvicorn 실행 ───────────────────────────────────────────────────────────
# exec로 PID 1을 uvicorn으로 교체 → SIGTERM이 직접 전달되어 graceful shutdown 보장
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
