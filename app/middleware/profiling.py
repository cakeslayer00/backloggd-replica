import time

from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

SLOW_THRESHOLD_MS = 500


class ProfilingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        profiling_enabled = (
            settings.PROFILING_ENABLED
            or request.headers.get("X-Profile") == "true"
        )

        if not profiling_enabled:
            return await call_next(request)

        profiler = Profiler(async_mode="enabled")
        profiler.start()

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        profiler.stop()

        output = profiler.output_text(unicode=True, color=False, show_all=False)

        if latency_ms >= SLOW_THRESHOLD_MS:
            print(
                f"\n[PROFILER][SLOW ENDPOINT DETECTED]\n"
                f"  endpoint : {request.url.path}\n"
                f"  method   : {request.method}\n"
                f"  latency  : {latency_ms:.2f}ms (threshold: {SLOW_THRESHOLD_MS}ms)\n"
                f"  profile  :\n{output}"
            )
        else:
            print(
                f"\n[PROFILER] {request.method} {request.url.path} "
                f"— {latency_ms:.2f}ms\n{output}"
            )

        response.headers["X-Process-Time-Ms"] = f"{latency_ms:.2f}"
        return response