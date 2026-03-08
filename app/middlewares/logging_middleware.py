from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from app.core.logging import set_trace_id, reset_trace_id, get_logger

# 使用默认日志（app_name）
logger = get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件，为每个请求生成 trace_id
    
    注意：这个中间件应该最后添加（在 FastAPI 中意味着最先执行），
    以确保包裹所有其他中间件，在数据库会话完全关闭后才重置 trace_id
    """
    
    async def dispatch(self, request: Request, call_next):
        # 生成 trace_id
        trace_id = str(uuid.uuid4())
        set_trace_id(trace_id)
        
        # 记录请求开始
        logger.info(f"Request started: {request.method} {request.url.path}")
        
        try:
            # 处理请求（这会进入内层中间件）
            response = await call_next(request)
            
            # 记录请求结束
            logger.info(f"Request completed: {request.method} {request.url.path} {response.status_code}")
            
            return response
        except Exception as e:
            # 记录异常
            logger.error(f"Request failed: {request.method} {request.url.path}", exc_info=True)
            raise
        finally:
            # 重置 trace_id - 确保在数据库会话关闭后才执行
            # 由于 FastAPI 中间件的执行顺序，这里会在所有内层中间件的 finally 之后执行
            reset_trace_id()
