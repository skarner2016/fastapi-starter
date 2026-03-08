import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings


def generate_jwt_token(user_id: str, name: str, email: str) -> str:
    """生成 JWT Token
    
    Args:
        user_id: 用户 ID
        name: 用户名
        email: 用户邮箱
    
    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id),  # 使用用户 ID 作为主题
        "name": name,  # 保留用户名信息
        "email": email,  # 保留邮箱信息
        "iat": now,  # 签发时间
        "exp": now + timedelta(seconds=settings.jwt_expiration),  # 过期时间
        "type": "access"
    }
    
    # 生成 JWT Token
    jwt_token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return jwt_token

def generate_6_digit_code() -> str:
    """生成随机的 6 位数字字符串"""
    import random
    import string
    return "".join(random.choices(string.digits, k=6))
    
