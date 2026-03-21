import redis.asyncio as redis
from app.core.config import settings

# Redis 连接池
redis_pool = None


async def init_redis_pool():
    """初始化 Redis 连接池"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True
        )


async def close_redis_pool():
    """关闭 Redis 连接池"""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


async def get_redis_pool():
    """获取 Redis 连接"""
    if redis_pool is None:
        await init_redis_pool()
    return redis.Redis(connection_pool=redis_pool)
