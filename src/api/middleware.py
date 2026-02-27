import logging
from urllib.parse import unquote
import typing
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi.responses import JSONResponse
from src.security import detect_injection, PromptInjectionError

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """
    전역 보안 필터 (Prompt Injection 등 악의적인 입력 감지 및 IP 로깅)
    Pure ASGI Middleware로 구현하여 스트리밍 및 비동기 컨텍스트 전파 문제 해결
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_host = scope.get("client", ("Unknown IP", 0))[0]

        try:
            # 1. 쿼리 파라미터 검증
            query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            if query_string:
                for param in query_string.split("&"):
                    if "=" in param:
                        _, value = param.split("=", 1)
                        if value:
                            detect_injection(unquote(value))
                    else:
                        if param:
                            detect_injection(unquote(param))

            # 2. 바디(Body) 검증
            headers = dict(scope.get("headers", []))
            content_type = headers.get(b"content-type", b"").decode("utf-8", errors="ignore")
            
            # 검증 범위 확장: json, form-urlencoded, multipart/form-data 등
            # 바이너리나 파일 업로드가 메인인 엔드포인트가 아님을 가정, 텍스트 기반 본문에 대해 검사를 시도
            if scope["method"] in ["POST", "PUT", "PATCH"] and (
                "application/json" in content_type or 
                "application/x-www-form-urlencoded" in content_type or
                "multipart/form-data" in content_type
            ):
                body = b""
                more_body = True
                
                # 본문 읽기 (Pure ASGI)
                while more_body:
                    message = await receive()
                    body += message.get("body", b"")
                    more_body = message.get("more_body", False)
                
                if body:
                    try:
                        body_str = body.decode("utf-8")
                        if body_str.strip():
                            detect_injection(body_str)
                    except UnicodeDecodeError:
                        pass # 바이너리 데이터 건너뜀
                
                body_returned = False
                async def fake_receive() -> typing.Dict[str, typing.Any]:
                    nonlocal body_returned
                    if not body_returned:
                        body_returned = True
                        return {
                            "type": "http.request",
                            "body": body,
                            "more_body": False
                        }
                    return await receive()
                
                await self.app(scope, fake_receive, send)
                return

            # 바디 검증이 필요 없는 경우 (GET 등)
            await self.app(scope, receive, send)
            
        except PromptInjectionError as e:
            req_id = uuid.uuid4().hex
            logger.warning(
                f"[Security] Blocked by Middleware. IP: {client_host} | Reason: {str(e)} (ReqID: {req_id})",
                extra={"event": "security_blocked", "client_ip": client_host, "request_id": req_id}
            )
            response = JSONResponse(
                status_code=403,
                content={"detail": f"Forbidden: {str(e)}", "error_type": "PromptInjectionError", "request_id": req_id}
            )
            await response(scope, receive, send)
        except Exception as e:
            req_id = uuid.uuid4().hex
            logger.error(f"[SecurityMiddleware] Unexpected error: {str(e)} (ReqID: {req_id})")
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "request_id": req_id}
            )
            await response(scope, receive, send)
