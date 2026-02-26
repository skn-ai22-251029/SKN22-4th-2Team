import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.router import router as api_v1_router
from src.utils import configure_json_logging
from src.secrets_manager import bootstrap_secrets

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

    # 3. CORS 로직 통합
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 실제 배포 시 ["https://your-frontend-domain.com"] 등으로 변경 권장
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. API Endpoints 라우터 통합
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
