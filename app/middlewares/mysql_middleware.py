from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.context import set_mysql_pool, reset_mysql_pool
from app.core.mysql import AsyncSessionLocal


class DBSessionMiddleware(BaseHTTPMiddleware):
    """数据库会话中间件
    
    为每个请求创建数据库会话，并通过上下文变量使其全局可用
    """
    
    async def dispatch(self, request: Request, call_next):
        # 创建新的数据库会话（不使用 async with，手动管理生命周期）
        session = AsyncSessionLocal()
        
        # 设置到上下文变量
        set_mysql_pool(session)
        
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
            # 关闭会话
            await session.close()
            # 清理上下文变量
            reset_mysql_pool()
