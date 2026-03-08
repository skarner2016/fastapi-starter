from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


class TimeoutMiddleware(BaseHTTPMiddleware):
    """超时中间件，当请求处理时间超过 APP_TIMEOUT 秒时中止请求"""

    async def dispatch(self, request: Request, call_next):
        # 从配置中获取超时时间
        timeout_seconds = settings.app_timeout

        try:
            # 使用 asyncio.wait_for 来设置超时
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            # 记录超时日志
            logger.error(
                f"Request timeout: {request.method} {request.url.path} "
                f"exceeded {timeout_seconds} seconds"
            )
            # 返回 408 Request Timeout 响应
            return JSONResponse(
                status_code=408,
                content={
                    "detail": f"Request timeout: The server timed out after {timeout_seconds} seconds"
                }
            )
