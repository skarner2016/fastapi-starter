import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from app.main import init_app
from app.api import api_router
from app.core.context import set_mysql_pool, reset_mysql_pool
from app.core.redis_context import set_redis, reset_redis
from app.core.mysql import AsyncSessionLocal
from app.core.redis import get_redis


class _TestDBMiddleware(BaseHTTPMiddleware):
    """测试专用的数据库会话中间件"""
    
    async def dispatch(self, request: Request, call_next):
        async with AsyncSessionLocal() as session:
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


class _TestRedisMiddleware(BaseHTTPMiddleware):
    """测试专用的 Redis 连接中间件"""
    
    async def dispatch(self, request: Request, call_next):
        redis_conn = await get_redis()
        set_redis(redis_conn)
        try:
            response = await call_next(request)
            return response
        finally:
            reset_redis()


@pytest.fixture(scope="function")
def client():
    """Create a TestClient with database session for each test function"""
    
    # 创建新的 app 实例用于测试
    test_app = init_app()
    test_app.add_middleware(_TestDBMiddleware)
    test_app.add_middleware(_TestRedisMiddleware)
    test_app.include_router(api_router)
    
    with TestClient(test_app) as c:
        yield c


def test_read_root(client):
    """Test GET /"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check(client):
    """Test GET /health"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_user(client):
    """Test POST /users"""
    response = client.post("/users", params={"name": "Test User", "email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Test User"
    assert data["data"]["email"] == "test@example.com"
    assert "id" in data["data"]


def test_get_users(client):
    """Test GET /users"""
    # First create a user
    client.post("/users", params={"name": "Test User 2", "email": "test2@example.com"})
    
    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


def test_get_user(client):
    """Test GET /users/{user_id}"""
    # First create a user
    create_response = client.post("/users", params={"name": "Test User 3", "email": "test3@example.com"})
    user_id = create_response.json()["data"]["id"]
    
    # Test getting the user
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["id"] == user_id
    assert data["data"]["name"] == "Test User 3"
    assert data["data"]["email"] == "test3@example.com"


def test_get_user_not_found(client):
    """Test GET /users/{user_id} with non-existent user"""
    response = client.get("/users/999999")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404
    assert data["message"] == "User not found"


def test_update_user(client):
    """Test PUT /users/{user_id}"""
    # First create a user
    create_response = client.post("/users", params={"name": "Test User 4", "email": "test4@example.com"})
    user_id = create_response.json()["data"]["id"]
    
    # Test updating the user
    response = client.put(f"/users/{user_id}", params={"name": "Updated User", "email": "updated@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "User updated"


def test_update_user_not_found(client):
    """Test PUT /users/{user_id} with non-existent user"""
    response = client.put("/users/999999", params={"name": "Updated User", "email": "updated@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404
    assert data["message"] == "User not found"


def test_delete_user(client):
    """Test DELETE /users/{user_id}"""
    # First create a user
    create_response = client.post("/users", params={"name": "Test User 5", "email": "test5@example.com"})
    user_id = create_response.json()["data"]["id"]
    
    # Test deleting the user
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "User deleted"


def test_delete_user_not_found(client):
    """Test DELETE /users/{user_id} with non-existent user"""
    response = client.delete("/users/999999")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 404
    assert data["message"] == "User not found"


def test_get_user_from_cache(client):
    """Test GET /users/cache/{user_id} - 测试从缓存获取用户数据"""
    # 1. 先创建一个用户
    create_response = client.post("/users", params={"name": "Cache Test User", "email": "cache@example.com"})
    user_id = create_response.json()["data"]["id"]
    
    # 2. 首次请求 - 应该从数据库获取并缓存
    response1 = client.get(f"/users/cache/{user_id}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["code"] == 0
    assert data1["data"]["id"] == user_id
    assert data1["data"]["name"] == "Cache Test User"
    assert data1["data"]["email"] == "cache@example.com"
    assert data1["source"] == "database"  # 首次应该来自数据库
    
    # 3. 再次请求 - 应该从缓存获取
    response2 = client.get(f"/users/cache/{user_id}")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["code"] == 0
    assert data2["data"]["id"] == user_id
    assert data2["data"]["name"] == "Cache Test User"
    assert data2["data"]["email"] == "cache@example.com"
    assert data2["source"] == "cache"  # 再次应该来自缓存
    
    # 4. 请求不存在的用户
    response3 = client.get("/users/cache/999999")
    assert response3.status_code == 200
    data3 = response3.json()
    assert data3["code"] == 404
    assert data3["message"] == "User not found"
