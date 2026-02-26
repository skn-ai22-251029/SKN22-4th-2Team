import os
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.router import router as api_v1_router
from src.utils import configure_json_logging
from src.secrets_manager import bootstrap_secrets
from src.api.middleware import SecurityMiddleware
from src.security import PromptInjectionError

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    # 0. 시크릿 부트스트랩 (AWS Secrets Manager / .env 로드)
    bootstrap_secrets()

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

    @app.get("/")
    async def root_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app

app = create_app()
