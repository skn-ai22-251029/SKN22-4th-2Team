import os
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 애플리케이션 모듈 임포트 전 가장 먼저 시크릿을 로드합니다.
# 이를 통해 모듈 레벨에서 값을 읽는 config 변수 등에 시크릿 값이 즉시 반영됩니다.
from src.secrets_manager import bootstrap_secrets
try:
    bootstrap_secrets()
except Exception as e:
    logging.getLogger(__name__).critical(f"Failed to load secrets initially: {e}. Exiting immediately.")
    import sys
    sys.exit(1)

from src.api.v1.router import router as api_v1_router
from src.utils import configure_json_logging
from src.api.middleware import SecurityMiddleware
from src.security import PromptInjectionError

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    # 1. 로깅 초기화
    configure_json_logging(level=logging.INFO)
    logger.info("Starting FastAPI application...")

    # 2. FastAPI 초기화
    app = FastAPI(
        title="쇼특허 (Short-Cut) API 명세서",
        description="AI 기반 특허 선행 기술 조사 시스템 Backend API",
        version="1.0.0",
    )

    # 3. 미들웨어 추가 (순서는 나중에 등록한 것이 먼저 실행됨)
    # CORS 도메인은 환경변수 또는 로컬호스트로 제한하여 보안 설정 원복 방지
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 보안 미들웨어 등록 (ASGI 기반)
    app.add_middleware(SecurityMiddleware)

    # 4. 전역 예외 처리 (Global Exception Handlers)
    @app.exception_handler(PromptInjectionError)
    async def prompt_injection_exception_handler(request: Request, exc: PromptInjectionError):
        req_id = uuid.uuid4().hex
        logger.error(f"[GlobalException] Prompt Injection at {request.url.path} from {request.client.host if request.client else 'Unknown'} (ReqID: {req_id})")
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Forbidden: 악의적인 입력 패턴이 감지되었습니다.", 
                "error_type": "PromptInjectionError",
                "request_id": req_id
            }
        )

    from src.rate_limiter import RateLimitException
    @app.exception_handler(RateLimitException)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
        req_id = uuid.uuid4().hex
        logger.warning(f"[RateLimit] Hit at {request.url.path} (ReqID: {req_id}): {exc.message}")
        return JSONResponse(
            status_code=429,
            content={
                "detail": exc.message,
                "reset_time": exc.reset_time,
                "request_id": req_id
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        req_id = uuid.uuid4().hex
        logger.error(f"[GlobalException] Unhandled Error at {request.url.path} (ReqID: {req_id}): {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "request_id": req_id
            }
        )

    # 5. API Endpoints 라우터 통합
    app.include_router(api_v1_router, prefix="/api/v1", tags=["analyze"])

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    @app.get("/")
    async def serve_index():
        """Root 경로 접속 시 프론트엔드 index.html 반환 (ALB 헬스체크 200 OK 포함)"""
        return FileResponse("frontend/index.html")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # 프론트엔드 폴더(app.js 등 정적 리소스) 마운트 (API 라우트 뒤에 배치)
    app.mount("/", StaticFiles(directory="frontend"), name="frontend")

    return app

app = create_app()
