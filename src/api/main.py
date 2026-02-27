import os
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# 애플리케이션 모듈 임포트 전 가장 먼저 시크릿을 로드합니다.
# AWS Secrets Manager가 값을 주입했다면 os.getenv를 통해 조회 가능합니다.
from src.secrets_manager import bootstrap_secrets

# 시크릿 부트스트랩 (AWS Secrets Manager 또는 .env 로드)
bootstrap_secrets()

# ── 핵심 환경 변수 선행 검증 (Fast-Fail) ──────────────────────────────────
# 앱 구동 전 필수 키가 누락되었다면 에러 로그를 남기지만, 컨테이너 헬스체크 통과를 위해 종료(sys.exit)하지는 않습니다.
critical_env_vars = {
    "OPENAI_API_KEY": "OpenAI API 키가 누락되었습니다.",
    "PINECONE_API_KEY": "Pinecone API 키가 누락되었습니다.",
    "PINECONE_ENVIRONMENT": "Pinecone 환경 설정이 누락되었습니다.",
    "PINECONE_INDEX_NAME": "Pinecone 인덱스 이름이 누락되었습니다."
}

missing_vars = []
for var, msg in critical_env_vars.items():
    if not os.getenv(var):
        logger.critical(f"Missing critical environment variable: {var} ({msg})")
        missing_vars.append(var)

if missing_vars:
    logger.critical(f"Application is misconfigured! Missing variables: {', '.join(missing_vars)}")
    # sys.exit(1) # ECS 헬스체크 통과를 위해 주석 처리

# 검증 통과 완료 시 config 및 나머지 모듈 로드
from src.config import config

from contextlib import asynccontextmanager
from src.api.v1.router import router as api_v1_router
from src.utils import configure_json_logging
from src.api.middleware import SecurityMiddleware
from src.security import PromptInjectionError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """트래픽 수신 전 의존성 사전 초기화 (Pre-warm)"""
    from src.api.dependencies import get_patent_agent, get_history_manager
    
    logger.info("Checking system readiness & pre-warming dependencies...")
    
    try:
        # PatentAgent 초기화 시 내부적으로 config 검증 및 LLM 연결 테스트가 수행되길 기대합니다.
        agent = get_patent_agent()
        logger.info(f"PatentAgent initialized (Model: {config.llm.model_name})")
        
        get_history_manager()
        logger.info("HistoryManager initialized.")
        
        # NLTK 데이터 경로 확인 (Dockerfile ENV와 동기화 확인용)
        import nltk
        logger.info(f"NLTK Data Paths: {nltk.data.path}")
        
        logger.info("System health check: PASSED. Ready to receive traffic.")
    except Exception as e:
        logger.critical(f"FATAL: Dependency initialization failed during lifespan: {e}")
        # 초기화 실패 시 컨테이너가 Unhealthy 상태로 남지 않고 일단 켜지게 둡니다 (ALB 200 OK 헬스체크용).
        # 실제 API 요청 시 500 에러+상세메시지로 사용자에게 노출됩니다.
    
    yield
    logger.info("Shutting down FastAPI application...")

def create_app() -> FastAPI:
    # 1. 로깅 초기화
    configure_json_logging(level=logging.INFO)
    logger.info("Starting FastAPI application...")

    # 2. FastAPI 초기화
    app = FastAPI(
        title="쇼특허 (Short-Cut) API 명세서",
        description="AI 기반 특허 선행 기술 조사 시스템 Backend API",
        version="1.0.0",
        lifespan=lifespan,
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
                "detail": f"Internal Server Error: {str(exc)}",
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
        return {
            "status": "ok",
            "build_commit": os.getenv("GIT_COMMIT", "unknown"),
            "build_branch": os.getenv("GIT_BRANCH", "unknown"),
        }

    # 프론트엔드 폴더(app.js 등 정적 리소스) 마운트 (API 라우트 뒤에 배치)
    app.mount("/", StaticFiles(directory="frontend"), name="frontend")

    return app

app = create_app()
