import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.logging import request_id_ctx, logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that reads X-Request-ID from incoming headers or generates a new UUID4.
    Sets the ContextVar for JSON logging and attaches X-Request-ID to response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id
            
            # Log request execution (except probes to reduce noise)
            if not request.url.path.startswith(("/health", "/ready", "/metrics")):
                logger.info(
                    f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')} - {response.status_code} ({duration_ms}ms)"
                )
            return response
        finally:
            request_id_ctx.reset(token)
