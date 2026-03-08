import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import typer
from typing import Optional

app = typer.Typer(help="FastAPI Starter CLI 工具")


@app.command()
def hello(name: str = typer.Option("World", help="要问候的名字")):
    """简单的问候命令"""
    typer.echo(f"Hello, {name}!")


@app.command()
def version():
    """显示版本信息"""
    typer.echo("FastAPI Starter CLI v1.0.0")



@app.command()
def test_redis():
    """测试 Redis 连接"""
    from app.core.redis import init_redis_pool, close_redis_pool, get_redis_pool
    
    async def test():
        typer.echo("正在连接 Redis...")
        await init_redis_pool()
        
        redis_conn = await get_redis_pool()
        await redis_conn.set("test_key", "test_value", ex=10)
        value = await redis_conn.get("test_key")
        
        typer.echo(f"Redis 连接成功！测试值: {value}")
        
        await close_redis_pool()
    
    import asyncio
    asyncio.run(test())


@app.command()
def test_mysql():
    """测试 MySQL 连接"""
    from app.core import init_mysql_pool, close_mysql_pool
    from app.core.mysql import AsyncSessionLocal
    from sqlalchemy import text
    
    async def test():
        typer.echo("正在连接 MySQL...")
        await init_mysql_pool()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            typer.echo(f"MySQL 连接成功！测试查询结果: {result.scalar()}")
        
        await close_mysql_pool()
    
    import asyncio
    asyncio.run(test())


if __name__ == "__main__":
    app()
