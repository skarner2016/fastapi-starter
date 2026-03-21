#!/usr/bin/env python3
"""
测试 MySQL 和 Redis 连接池是否生效
"""

import asyncio
import time
from app.core.mysql import init_mysql_pool, close_mysql_pool
from app.core.redis import init_redis_pool, close_redis_pool
from app.core.mysql import AsyncSessionLocal
from app.core.redis import get_redis_pool


async def test_mysql_connection_pool():
    """测试 MySQL 连接池"""
    print("=== 测试 MySQL 连接池 ===")
    
    # 初始化数据库连接池
    await init_mysql_pool()
    print("MySQL 连接池初始化完成")
    
    try:
        # 测试连接复用
        connections = []
        start_time = time.time()
        
        # 创建多个会话，测试连接池是否复用连接
        for i in range(5):
            session = AsyncSessionLocal()
            connections.append(session)
            print(f"创建会话 {i+1}")
        
        # 关闭所有会话
        for i, session in enumerate(connections):
            await session.close()
            print(f"关闭会话 {i+1}")
        
        elapsed = time.time() - start_time
        print(f"创建和关闭 5 个会话耗时: {elapsed:.4f} 秒")
        
        # 测试并发创建会话
        print("\n测试并发创建会话...")
        
        async def create_session():
            session = AsyncSessionLocal()
            try:
                # 仅创建和持有会话，不执行查询
                pass
            finally:
                await session.close()
        
        start_time = time.time()
        tasks = [create_session() for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        print(f"并发创建和关闭 10 个会话耗时: {elapsed:.4f} 秒")
        
    finally:
        await close_mysql_pool()
        print("MySQL 连接池关闭完成")


async def test_redis_connection_pool():
    """测试 Redis 连接池"""
    print("\n=== 测试 Redis 连接池 ===")
    
    # 初始化 Redis 连接池
    await init_redis_pool()
    print("Redis 连接池初始化完成")
    
    try:
        # 测试连接复用
        connections = []
        start_time = time.time()
        
        # 获取多个连接，测试连接池是否复用连接
        for i in range(5):
            conn = await get_redis_pool()
            connections.append(conn)
            print(f"获取连接 {i+1}")
        
        elapsed = time.time() - start_time
        print(f"获取 5 个连接耗时: {elapsed:.4f} 秒")
        
        # 测试并发获取连接
        print("\n测试并发获取连接...")
        
        async def get_connection():
            conn = await get_redis_pool()
            try:
                # 仅获取连接，不执行命令
                pass
            finally:
                # Redis 连接不需要手动关闭，连接池会管理
                pass
        
        start_time = time.time()
        tasks = [get_connection() for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        print(f"并发获取 10 个连接耗时: {elapsed:.4f} 秒")
        
    finally:
        await close_redis_pool()
        print("Redis 连接池关闭完成")


async def main():
    """主测试函数"""
    await test_mysql_connection_pool()
    await test_redis_connection_pool()
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
