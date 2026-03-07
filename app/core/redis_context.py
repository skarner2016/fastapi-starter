from contextvars import ContextVar
import redis.asyncio as redis

# 全局上下文变量，存储当前请求的 Redis 连接
redis_client: ContextVar[redis.Redis | None] = ContextVar('redis_client', default=None)


def get_redis() -> redis.Redis:
    """获取当前请求的 Redis 连接
    
    使用方式：
        redis_conn = get_redis()
        await redis_conn.set('key', 'value')
    """
    client = redis_client.get()
    if client is None:
        raise RuntimeError("No Redis client available. Make sure you're within a request context.")
    return client


def set_redis(client: redis.Redis) -> None:
    """设置当前请求的 Redis 连接（由中间件调用）"""
    redis_client.set(client)


def reset_redis() -> None:
    """重置 Redis 连接（由中间件调用）"""
    redis_client.set(None)
