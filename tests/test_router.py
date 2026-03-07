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
from app.core.context import set_db, reset_db
from app.core.mysql import AsyncSessionLocal


class _TestDBMiddleware(BaseHTTPMiddleware):
    """测试专用的数据库会话中间件"""
    
    async def dispatch(self, request: Request, call_next):
        async with AsyncSessionLocal() as session:
            set_db(session)
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
                reset_db()


@pytest.fixture(scope="function")
def client():
    """Create a TestClient with database session for each test function"""
    
    # 创建新的 app 实例用于测试
    test_app = init_app()
    test_app.add_middleware(_TestDBMiddleware)
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
