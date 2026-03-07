from contextlib import asynccontextmanager
from app.core import init_db, close_db
from fastapi import FastAPI
from app.api import api_router
from app.core import settings
from app.core.middleware import DBSessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print(f"Initializing {settings.app_name}...")

    await init_db()
    print("Database initialized")
    
    yield
    # Shutdown
    print("Shutting down...")
    
    await close_db()
    print("Database closed")


def init_app() -> FastAPI:
    """初始化应用"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=f"{settings.app_name} API",
        lifespan=lifespan,
    )
    
    # 添加数据库会话中间件
    app.add_middleware(DBSessionMiddleware)
    
    app.include_router(api_router)

    return app


# Create app instance
app = init_app()

if __name__ == "__main__":
    import uvicorn

    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    
    app_module = "app.main:app"
    host = "0.0.0.0"
    port=8000

    if "prd" == settings.app_env:
        uvicorn.run(
            app_module,
            host=host,
            port=port,
            workers=4,
        )
    else:
        uvicorn.run(
            app_module,
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app"],  # watchfiles 只监控 app 目录
        )
