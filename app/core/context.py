from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

# 全局上下文变量，存储当前请求的数据库会话
mysql_pool_session: ContextVar[AsyncSession | None] = ContextVar('mysql_pool_session', default=None)


def get_mysql_pool() -> AsyncSession:
    """获取当前请求的数据库会话
    
    使用方式：
        db = get_mysql_pool()
        result = await db.execute(...)
    """
    session = mysql_pool_session.get()
    if session is None:
        raise RuntimeError("No database session available. Make sure you're within a request context.")
    return session


def set_mysql_pool(session: AsyncSession) -> None:
    """设置当前请求的数据库会话（由中间件调用）"""
    mysql_pool_session.set(session)


def reset_mysql_pool() -> None:
    """重置数据库会话（由中间件调用）"""
    mysql_pool_session.set(None)
