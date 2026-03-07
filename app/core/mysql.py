from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core import settings

# 同步引擎（用于迁移）
sync_engine = create_engine(
    settings.mysql_url.replace('mysql://', 'mysql+pymysql://'),
    pool_size=settings.mysql_pool_size,
    pool_recycle=settings.mysql_pool_recycle,
    echo=False
)

# 异步引擎
async_engine = create_async_engine(
    settings.mysql_url.replace('mysql://', 'mysql+aiomysql://'),
    pool_size=settings.mysql_pool_size,
    pool_recycle=settings.mysql_pool_recycle,
    pool_pre_ping=True,
    max_overflow=10,
    pool_timeout=30,
    echo=settings.app_debug  # 生产环境关闭
)

# 会话工厂
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 基础模型类
Base = declarative_base()


# 依赖项
def get_db() -> Session:
    """Get sync database session"""
    db = sessionmaker(sync_engine)()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database"""
    pass


async def close_db():
    """Close database connection"""
    await async_engine.dispose()
