import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
import time
from fastapi import Request, FastAPI
from httpx import AsyncClient, ASGITransport
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.api import api_router
from app.core.context import set_mysql_pool, reset_mysql_pool
from app.core.redis_context import set_redis, reset_redis
from app.core.logging_middleware import LoggingMiddleware
from app.core import settings


# 测试专用的 MySQL 引擎（使用 NullPool 避免连接池问题）
def create_test_engine():
    """创建测试引擎"""
    return create_async_engine(
        settings.mysql_url.replace('mysql://', 'mysql+aiomysql://'),
        poolclass=NullPool,  # 使用 NullPool，不缓存连接
        echo=False
    )


def create_test_session(engine):
    """创建测试会话工厂"""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


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
        set_redis(redis_conn)
        try:
            response = await call_next(request)
            return response
        finally:
            reset_redis()


@pytest_asyncio.fixture(scope="session")
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
    
    test_app = FastAPI()
    
    # 添加测试用的中间件（逆序添加，最后添加的最外层）
    test_app.add_middleware(_TestRedisMiddleware)
    test_app.add_middleware(_TestDBMiddleware)
    test_app.add_middleware(LoggingMiddleware)
    
    # 复制路由
    test_app.include_router(api_router)
    
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_read_root(async_client):
    """Test root endpoint"""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test health check endpoint"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_user(async_client):
    """Test create user endpoint"""
    import time
    email = f"test_{int(time.time() * 1000)}@example.com"
    response = await async_client.post(f"/users?name=Test%20User&email={email}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_users(async_client):
    """Test get users endpoint"""
    response = await async_client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_user(async_client):
    """Test get user by ID endpoint"""
    import time
    email = f"test_get_{int(time.time() * 1000)}@example.com"
    create_response = await async_client.post(f"/users?name=Test%20User&email={email}")
    user_id = create_response.json()["data"]["id"]
    
    response = await async_client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_user_not_found(async_client):
    """Test get user by ID endpoint - user not found"""
    response = await async_client.get("/users/99999")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_update_user(async_client):
    """Test update user endpoint"""
    import time
    email = f"test_update_{int(time.time() * 1000)}@example.com"
    create_response = await async_client.post(f"/users?name=Test%20User&email={email}")
    user_id = create_response.json()["data"]["id"]
    
    response = await async_client.put(f"/users/{user_id}?name=Updated%20User&email=updated_{int(time.time() * 1000)}@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_update_user_not_found(async_client):
    """Test update user endpoint - user not found"""
    response = await async_client.put("/users/99999?name=Updated%20User&email=updated@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_delete_user(async_client):
    """Test delete user endpoint"""
    import time
    email = f"test_delete_{int(time.time() * 1000)}@example.com"
    create_response = await async_client.post(f"/users?name=Test%20User&email={email}")
    user_id = create_response.json()["data"]["id"]
    
    response = await async_client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_delete_user_not_found(async_client):
    """Test delete user endpoint - user not found"""
    response = await async_client.delete("/users/99999")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_get_user_from_cache(async_client):
    """Test get user from cache endpoint"""
    import time
    email = f"test_cache_{int(time.time() * 1000)}@example.com"
    create_response = await async_client.post(f"/users?name=Test%20User&email={email}")
    user_id = create_response.json()["data"]["id"]
    
    # First call - should get from database
    response1 = await async_client.get(f"/users/cache/{user_id}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["code"] == 0
    assert data1["source"] == "database"
    
    # Second call - should get from cache
    response2 = await async_client.get(f"/users/cache/{user_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["code"] == 0
    assert data2["source"] == "cache"


@pytest.mark.asyncio
async def test_stream_timestamps(async_client):
    """Test stream timestamps endpoint"""
    # Test with 2 seconds to keep the test fast
    seconds = 2
    start_time = time.time()
    
    # Send request to streaming endpoint
    async with async_client.stream("GET", f"/stream/timestamps?seconds={seconds}") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # Read the streaming response
        lines = []
        async for line in response.aiter_lines():
            if line:
                lines.append(line)
        
        # Verify we received the expected number of timestamps
        # We should get 'seconds' timestamp lines plus 1 success line
        assert len(lines) == seconds + 1
        
        # Verify the first 'seconds' lines are timestamps
        for i in range(seconds):
            assert lines[i].startswith("Timestamp:")
        
        # Verify the last line is the success message
        assert lines[-1] == f"Success: Stream completed after {seconds} seconds"
    
    # Verify the request took at least 'seconds' seconds
    elapsed_time = time.time() - start_time
    assert elapsed_time >= seconds
