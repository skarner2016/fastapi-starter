from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.context import set_db, reset_db
from app.core.mysql import AsyncSessionLocal


class DBSessionMiddleware(BaseHTTPMiddleware):
    """数据库会话中间件
    
    为每个请求创建数据库会话，并通过上下文变量使其全局可用
    """
    
    async def dispatch(self, request: Request, call_next):
        # 创建新的数据库会话
        async with AsyncSessionLocal() as session:
            # 设置到上下文变量
            set_db(session)
            
            try:
                # 处理请求
                response = await call_next(request)
                
                # 提交事务（如果响应成功）
                if response.status_code < 400:
                    await session.commit()
                else:
                    await session.rollback()
                
                return response
                
            except Exception as e:
                # 发生异常时回滚
                await session.rollback()
                raise
            finally:
                # 清理上下文变量
                reset_db()
