from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_context import set_redis, reset_redis
from app.core.redis import get_redis_pool


class RedisSessionMiddleware(BaseHTTPMiddleware):
    """Redis 连接中间件
    
    为每个请求创建 Redis 连接，并通过上下文变量使其全局可用
    """
    
    async def dispatch(self, request: Request, call_next):
        # 获取 Redis 连接
        redis_conn = await get_redis_pool()
        
        # 设置到上下文变量
        set_redis(redis_conn)
        
        try:
            # 处理请求
            response = await call_next(request)
            return response
        finally:
            # 清理上下文变量
            reset_redis()
