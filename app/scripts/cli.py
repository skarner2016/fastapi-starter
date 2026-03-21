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


@app.command()
def get_user(
    user_id: Optional[int] = typer.Option(None, "--id", help="用户ID"),
    email: Optional[str] = typer.Option(None, "--email", help="用户邮箱")
):
    """使用 ORM 获取用户数据"""
    from app.core import init_mysql_pool, close_mysql_pool
    from app.core.mysql import AsyncSessionLocal
    from app.models.user_model import UserModel
    from sqlalchemy import select
    
    async def fetch_user():
        if not user_id and not email:
            typer.echo("错误: 请提供 --id 或 --email 参数", err=True)
            raise typer.Exit(1)
        
        typer.echo("正在连接数据库...")
        await init_mysql_pool()
        
        async with AsyncSessionLocal() as db:
            # 构建查询条件
            if user_id:
                typer.echo(f"正在查询用户 ID: {user_id}")
                result = await db.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
            else:
                typer.echo(f"正在查询用户邮箱: {email}")
                result = await db.execute(
                    select(UserModel).where(UserModel.email == email)
                )
            
            user = result.scalar_one_or_none()
            
            if user is None:
                typer.echo("用户不存在")
            else:
                typer.echo("=" * 50)
                typer.echo(f"用户ID: {user.id}")
                typer.echo(f"用户名: {user.name}")
                typer.echo(f"邮箱: {user.email}")
                typer.echo(f"创建时间: {user.created_at}")
                typer.echo("=" * 50)
        
        await close_mysql_pool()
    
    import asyncio
    asyncio.run(fetch_user())


if __name__ == "__main__":
    app()
