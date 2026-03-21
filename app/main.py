from contextlib import asynccontextmanager
from app.core.mysql import init_mysql_pool, close_mysql_pool
from app.core.redis import init_redis_pool, close_redis_pool
from app.core.logging import init_logging
from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
from app.core.exception import register_exceptions
from app.middlewares.mysql_middleware import DBSessionMiddleware
from app.middlewares.redis_middleware import RedisSessionMiddleware
from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.timeout_middleware import TimeoutMiddleware
from app.middlewares.jwt_middleware import JWTMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print(f"Initializing {settings.app_name}...")
    
    # 初始化日志
    init_logging()
    print("Logging initialized")

    await init_mysql_pool()
    print("Database initialized")
    
    await init_redis_pool()
    print("Redis initialized")
    
    yield
    # Shutdown
    print("Shutting down...")
    
    await close_redis_pool()
    print("Redis closed")
    
    await close_mysql_pool()
    print("Database closed")


def init_app() -> FastAPI:
    """初始化应用
    
    中间件执行顺序（从内到外，按添加顺序的逆序）：
    1. RedisSessionMiddleware（最先添加，最内层）
    2. DBSessionMiddleware
    3. JWTMiddleware
    4. TimeoutMiddleware
    5. LoggingMiddleware（最后添加，最外层，最后清理 trace_id）
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=f"{settings.app_name} API",
        lifespan=lifespan,
    )

    # 异常处理
    register_exceptions(app)

    # 注意：FastAPI 中间件按添加的逆序执行
    # 最后添加的中间件会在最外层执行，其 finally 块最后执行
    
    # 1. 添加 Redis 连接中间件（最内层）
    app.add_middleware(RedisSessionMiddleware)
    
    # 2. 添加数据库会话中间件
    app.add_middleware(DBSessionMiddleware)
    
    # 3. 添加 JWT 中间件
    app.add_middleware(JWTMiddleware)
    
    # 4. 添加超时中间件
    app.add_middleware(TimeoutMiddleware)
    
    # 5. 添加日志中间件（最外层，最后执行 finally 清理 trace_id）
    app.add_middleware(LoggingMiddleware)
    
    app.include_router(api_router)

    return app


# Create app instance
app = init_app()

if __name__ == "__main__":
    import uvicorn

    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    
    app_module = "app.main:app"
    host = "0.0.0.0"
    port = 8000
    
    # 根据环境配置参数
    if settings.app_env != "prd":
        uvicorn.run(app_module, host=host, port=port, reload=True, access_log=False)
    else:
        uvicorn.run(app_module, host=host, port=port, reload=False, workers=4, access_log=False)
