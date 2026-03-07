from fastapi import APIRouter
from sqlalchemy import select
from app.core.context import get_db
from app.model import UserModel

api_router = APIRouter()


@api_router.get("/")
def read_root():
    return {"message": "Hello World"}


@api_router.get("/health")
def health_check():
    return {"status": "ok"}


@api_router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID - 使用 ContextVar 获取数据库连接"""
    db = get_db()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        return {"code": 0, "data": {"id": user.id, "name": user.name, "email": user.email}}
    return {"code": 404, "message": "User not found"}


@api_router.get("/users")
async def get_users():
    """Get all users - 使用 ContextVar 获取数据库连接"""
    db = get_db()
    result = await db.execute(select(UserModel).limit(100))
    users = result.scalars().all()
    return {"code": 0, "data": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}


@api_router.post("/users")
async def create_user(name: str, email: str):
    """Create user - 使用 ContextVar 获取数据库连接"""
    db = get_db()
    user = UserModel(name=name, email=email)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return {"code": 0, "data": {"id": user.id, "name": user.name, "email": user.email}}


@api_router.put("/users/{user_id}")
async def update_user(user_id: int, name: str, email: str):
    """Update user - 使用 ContextVar 获取数据库连接"""
    db = get_db()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.name = name
        user.email = email
        await db.flush()
        return {"code": 0, "message": "User updated"}
    return {"code": 404, "message": "User not found"}


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user - 使用 ContextVar 获取数据库连接"""
    db = get_db()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.flush()
        return {"code": 0, "message": "User deleted"}
    return {"code": 404, "message": "User not found"}
