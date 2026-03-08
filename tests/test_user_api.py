import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from fastapi import Request, FastAPI
from httpx import AsyncClient, ASGITransport
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.api import api_router
from app.core.context import set_mysql_pool, reset_mysql_pool
from app.core.context import set_redis_pool, reset_redis_pool, get_redis_pool
from app.core import settings
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.jwt_middleware import JWTMiddleware


# 测试专用的 MySQL 引擎（使用 NullPool 避免连接池问题）
def create_test_engine():
    """创建测试引擎"""
    return create_async_engine(
        settings.mysql_url.replace("mysql://", "mysql+aiomysql://"),
        poolclass=NullPool,  # 使用 NullPool，不缓存连接
        echo=False,
    )


def create_test_session(engine):
    """创建测试会话工厂"""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class _TestDBMiddleware(BaseHTTPMiddleware):
    """测试专用的数据库会话中间件"""

    async def dispatch(self, request: Request, call_next):
        # 每次请求都创建新的引擎和会话
        engine = create_test_engine()
        SessionLocal = create_test_session(engine)

        async with SessionLocal() as session:
            set_mysql_pool(session)
            try:
                response = await call_next(request)
                if response.status_code < 400:
                    await session.commit()
                else:
                    await session.rollback()
                return response
            except Exception:
                await session.rollback()
                raise
            finally:
                reset_mysql_pool()
                await engine.dispose()


class _TestRedisMiddleware(BaseHTTPMiddleware):
    """测试专用的 Redis 连接中间件"""

    async def dispatch(self, request: Request, call_next):
        from app.core.redis import get_redis_pool

        redis_conn = await get_redis_pool()
        set_redis_pool(redis_conn)
        try:
            response = await call_next(request)
            return response
        finally:
            reset_redis_pool()


def create_test_app() -> FastAPI:
    """创建测试应用，复用生产环境的中间件配置
    
    中间件执行顺序（从内到外，按添加顺序的逆序）：
    1. _TestRedisMiddleware（最先添加，最内层）
    2. _TestDBMiddleware
    3. JWTMiddleware
    4. LoggingMiddleware（最后添加，最外层）
    """
    app = FastAPI()
    
    # 添加测试用的中间件（逆序添加，最后添加的最外层）
    # 复用 app/main.py 中的中间件配置，但替换数据库和Redis中间件为测试专用的
    app.add_middleware(_TestRedisMiddleware)
    app.add_middleware(_TestDBMiddleware)
    app.add_middleware(JWTMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # 复制路由
    app.include_router(api_router)
    
    return app


@pytest_asyncio.fixture(scope="function")
async def setup_databases():
    """设置测试数据库连接"""
    from app.core.redis import init_redis_pool, close_redis_pool
    
    # 初始化 Redis
    await init_redis_pool()
    
    yield
    
    # 清理 - 忽略事件循环已关闭的错误
    try:
        await close_redis_pool()
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise


@pytest_asyncio.fixture
async def async_client(setup_databases):
    """Create async test client"""
    from app.core.redis import init_redis_pool

    # 确保 Redis 已初始化
    await init_redis_pool()

    # 使用 create_test_app() 创建测试应用，复用生产环境的中间件配置
    test_app = create_test_app()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test health check endpoint"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["code"] == 0


@pytest.mark.asyncio
async def test_sms_code(async_client):
    """Test sms code endpoint"""
    response = await async_client.post(
        "/user/sms-code", json={"email": "test@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["code"] == 0


@pytest.mark.asyncio
async def test_login(async_client):
    """Test login endpoint"""
    email = "test@example.com"
    # 1. 先发送验证码
    sms_response = await async_client.post("/user/sms-code", json={"email": email})
    assert sms_response.status_code == 200
    sms_data = sms_response.json()
    assert sms_data["code"] == 0

    # 2. 从 Redis 中获取验证码（需要直接访问 Redis）
    from app.core.redis import get_redis_pool as get_redis_pool_direct

    redis_conn = await get_redis_pool_direct()
    code = await redis_conn.get(email)
    assert code is not None, "验证码未生成"

    # 3. 使用验证码登录
    response = await async_client.post(
        "/user/login", json={"email": email, "code": code}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0

    # 4. 验证返回结果（可能是注册成功或登录成功）
    assert isinstance(response_data["data"]["jwt_token"], str)

    # 5. 验证 token 是否有效（需要直接访问 Redis）
    info_response = await async_client.post(
        "/user/info", headers={"Authorization": f"Bearer {response_data['data']['jwt_token']}"}
    )
    assert info_response.status_code == 200
    info_response_data = info_response.json()
    print(f"Bearer {response_data['data']['jwt_token']}")
    print(f"info_response_data: {info_response_data}")
    assert info_response_data["code"] == 0
    assert info_response_data["data"]["email"] == email
