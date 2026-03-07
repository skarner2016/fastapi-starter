from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

# 全局上下文变量，存储当前请求的数据库会话
db_session: ContextVar[AsyncSession | None] = ContextVar('db_session', default=None)


def get_db() -> AsyncSession:
    """获取当前请求的数据库会话
    
    使用方式：
        db = get_db()
        result = await db.execute(...)
    """
    session = db_session.get()
    if session is None:
        raise RuntimeError("No database session available. Make sure you're within a request context.")
    return session


def set_db(session: AsyncSession) -> None:
    """设置当前请求的数据库会话（由中间件调用）"""
    db_session.set(session)


def reset_db() -> None:
    """重置数据库会话（由中间件调用）"""
    db_session.set(None)
