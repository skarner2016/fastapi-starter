from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
import json
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
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 处理请求（这会进入内层中间件）
            response = await call_next(request)
            
            # 计算响应时间（毫秒）
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录请求完成（JSON 格式）
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }
            logger.info(json.dumps(log_data))
            
            return response
        except Exception as e:
            # 计算响应时间（毫秒）
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录异常（JSON 格式）
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            }
            logger.error(json.dumps(log_data), exc_info=True)
            raise
        finally:
            # 重置 trace_id - 确保在数据库会话关闭后才执行
            # 由于 FastAPI 中间件的执行顺序，这里会在所有内层中间件的 finally 之后执行
            reset_trace_id()
