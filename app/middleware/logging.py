import time
import asyncio
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.elasticsearch import es_client

INDEX = "game-backlog-logs"


def get_log_type(status_code: int) -> str:
    if status_code >= 500:
        return "ERROR"
    if status_code >= 400:
        return "DEBUG"
    return "INFO"


def get_client_ip(request: Request) -> tuple[str, int]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    port = request.client.port if request.client else 0
    return ip, port


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            raise exc
        finally:
            processing_time = (time.perf_counter() - start_time) * 1000
            ip, port = get_client_ip(request)
            log_type = get_log_type(status_code)

            message = (
                f"{ip}:{port} - {request.method} - "
                f"{request.url} - {status_code} - "
                f"{processing_time:.2f}ms"
            )

            # print to stdout as well so you see it in uvicorn logs
            print(f"[{log_type}] {message}")

            # ship to ES asynchronously — fire and forget
            # if ES is down we don't want to crash the app
            asyncio.create_task(
                self._ship_to_es(
                    log_type=log_type,
                    message=message,
                    request=request,
                    status_code=status_code,
                    processing_time=processing_time,
                    ip=ip,
                    port=port,
                )
            )

        return response

    async def _ship_to_es(
        self,
        log_type: str,
        message: str,
        request: Request,
        status_code: int,
        processing_time: float,
        ip: str,
        port: int,
    ) -> None:
        try:
            await es_client.index(
                index=INDEX,
                document={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "log_type": log_type,
                    "service": "game-backlog-api",
                    "endpoint": request.url.path,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": status_code,
                    "processing_time_ms": round(processing_time, 2),
                    "ip": ip,
                    "port": port,
                    "message": message,
                },
            )
        except Exception:
            pass