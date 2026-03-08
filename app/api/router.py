from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.core.context import get_mysql_pool
from app.core.redis_context import get_redis
from app.core import get_logger
from app.model import UserModel
import asyncio
import time

api_router = APIRouter()
# 使用默认日志（app_name）
logger = get_logger()


@api_router.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World"}


@api_router.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}


@api_router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID - 使用 ContextVar 获取数据库连接"""
    logger.info(f"Getting user with ID: {user_id}")
    db = get_mysql_pool()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        logger.info(f"Found user: {user.name}")
        return {"code": 0, "data": {"id": user.id, "name": user.name, "email": user.email}}
    logger.warning(f"User not found with ID: {user_id}")
    return {"code": 404, "message": "User not found"}


@api_router.get("/users")
async def get_users():
    """Get all users - 使用 ContextVar 获取数据库连接"""
    logger.info("Getting all users")
    db = get_mysql_pool()
    result = await db.execute(select(UserModel).limit(100))
    users = result.scalars().all()
    logger.info(f"Found {len(users)} users")
    return {"code": 0, "data": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}


@api_router.post("/users")
async def create_user(name: str, email: str):
    """Create user - 使用 ContextVar 获取数据库连接"""
    logger.info(f"Creating user: {name} ({email})")
    db = get_mysql_pool()
    user = UserModel(name=name, email=email)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info(f"Created user with ID: {user.id}")
    return {"code": 0, "data": {"id": user.id, "name": user.name, "email": user.email}}


@api_router.put("/users/{user_id}")
async def update_user(user_id: int, name: str, email: str):
    """Update user - 使用 ContextVar 获取数据库连接"""
    logger.info(f"Updating user with ID: {user_id}")
    db = get_mysql_pool()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.name = name
        user.email = email
        await db.flush()
        logger.info(f"Updated user: {user.name}")
        return {"code": 0, "message": "User updated"}
    logger.warning(f"User not found with ID: {user_id}")
    return {"code": 404, "message": "User not found"}


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user - 使用 ContextVar 获取数据库连接"""
    logger.info(f"Deleting user with ID: {user_id}")
    db = get_mysql_pool()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.flush()
        logger.info(f"Deleted user: {user.name}")
        return {"code": 0, "message": "User deleted"}
    logger.warning(f"User not found with ID: {user_id}")
    return {"code": 404, "message": "User not found"}


@api_router.post("/redis/test")
async def test_redis(key: str = Query(...), value: str = Query(...)):
    """Test Redis functionality - 使用 ContextVar 获取 Redis 连接"""
    logger.info(f"Testing Redis with key: {key}")
    redis_conn = get_redis()
    await redis_conn.set(key, value)
    stored_value = await redis_conn.get(key)
    logger.info(f"Redis test completed for key: {key}")
    return {"code": 0, "data": {"key": key, "value": stored_value}}


@api_router.get("/redis/test/{key}")
async def get_redis_value(key: str):
    """Get value from Redis - 使用 ContextVar 获取 Redis 连接"""
    logger.info(f"Getting Redis value for key: {key}")
    redis_conn = get_redis()
    value = await redis_conn.get(key)
    if value:
        logger.info(f"Found Redis value for key: {key}")
        return {"code": 0, "data": {"key": key, "value": value}}
    logger.warning(f"Redis key not found: {key}")
    return {"code": 404, "message": "Key not found"}


@api_router.delete("/redis/test/{key}")
async def delete_redis_key(key: str):
    """Delete key from Redis - 使用 ContextVar 获取 Redis 连接"""
    logger.info(f"Deleting Redis key: {key}")
    redis_conn = get_redis()
    await redis_conn.delete(key)
    logger.info(f"Deleted Redis key: {key}")
    return {"code": 0, "message": "Key deleted"}


@api_router.get("/users/cache/{user_id}")
async def get_user_from_cache(user_id: int):
    """Get user from cache - 从 Redis 缓存中获取用户数据"""
    logger.info(f"Getting user from cache: {user_id}")
    redis_conn = get_redis()
    
    # 构建 Redis 键
    cache_key = f"user:{user_id}"
    
    # 从 Redis 中获取用户数据
    cached_user = await redis_conn.get(cache_key)
    
    if cached_user:
        import json
        user_data = json.loads(cached_user)
        logger.info(f"Found user in cache: {user_id}")
        return {"code": 0, "data": user_data, "source": "cache"}
    
    # 如果缓存中没有，从数据库获取
    db = get_mysql_pool()
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        # 构建用户数据
        user_data = {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
        
        # 缓存到 Redis，设置过期时间为 5 分钟
        import json
        await redis_conn.setex(
            cache_key,
            300,  # 5 分钟过期
            json.dumps(user_data)
        )
        logger.info(f"Cached user: {user.name}")
        return {"code": 0, "data": user_data, "source": "database"}
    
    logger.warning(f"User not found with ID: {user_id}")
    return {"code": 404, "message": "User not found"}


@api_router.get("/stream/timestamps")
async def stream_timestamps(seconds: int = Query(..., description="Number of seconds to stream timestamps")):
    """Stream timestamps every second for M seconds"""
    logger.info(f"Streaming timestamps for {seconds} seconds")
    
    async def timestamp_generator():
        for _ in range(seconds):
            current_time = time.time()
            yield f"Timestamp: {current_time}\n"
            await asyncio.sleep(1)
            # 检查是否超时
            logger.info(f"Stream completed {time.time()} seconds")
            
        yield f"Success: Stream completed after {seconds} seconds\n"
    
    return StreamingResponse(timestamp_generator(), media_type="text/plain")


@api_router.get("/test/timeout")
async def test_timeout(sleep_seconds: int = Query(default=15, description="Seconds to sleep")):
    """Test timeout functionality - sleeps for specified seconds"""
    logger.info(f"Test timeout endpoint started, will sleep for {sleep_seconds} seconds")
    await asyncio.sleep(sleep_seconds)
    logger.info(f"Test timeout endpoint completed")
    return {"message": f"Slept for {sleep_seconds} seconds"}
