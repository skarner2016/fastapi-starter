"""
业务日志使用示例

演示如何使用不同名称的 logger 将日志写入不同的目录
"""

import sys
sys.path.insert(0, '/Users/skarner/workspace/skarner2016/fastapi-starter')

from app.core.logging import get_logger, init_logging

# 初始化日志配置
init_logging()

# 1. 默认日志 - 写入 runtime/logs/fastapi-starter/fastapi-starter.log
default_logger = get_logger()
default_logger.info("This is a default log message")
default_logger.warning("This is a default warning message")

# 2. 黑名单业务日志 - 写入 runtime/logs/blacklist/blacklist.log
blacklist_logger = get_logger('blacklist')
blacklist_logger.info("Blacklist user added: user_id=123")
blacklist_logger.warning("Blacklist user removed: user_id=456")

# 3. 用户业务日志 - 写入 runtime/logs/user/user.log
user_logger = get_logger('user')
user_logger.info("User logged in: user_id=789")
user_logger.error("User login failed: email=test@example.com")

# 4. 订单业务日志 - 写入 runtime/logs/order/order.log
order_logger = get_logger('order')
order_logger.info("Order created: order_id=1001, amount=99.99")
order_logger.info("Order completed: order_id=1001")

print("日志写入完成！")
print("\n日志文件位置：")
print("  - 默认日志: runtime/logs/fastapi-starter/fastapi-starter.log")
print("  - 黑名单日志: runtime/logs/blacklist/blacklist.log")
print("  - 用户日志: runtime/logs/user/user.log")
print("  - 订单日志: runtime/logs/order/order.log")
