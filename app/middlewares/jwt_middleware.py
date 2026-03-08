from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
from app.core import settings
from app.core.context import set_current_user_id, reset_current_user_id, get_current_user_id


class JWTMiddleware(BaseHTTPMiddleware):
    """JWT 中间件

    解析请求头中的 JWT Token，并将用户 ID 存储到上下文变量中
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 重置用户 ID（确保每个请求都是独立的）
        reset_current_user_id()

        try:
            # 从请求头中获取 Authorization
            authorization = request.headers.get("Authorization")

            # 检查 Authorization 头
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]

                try:
                    # 解析 JWT Token
                    payload = jwt.decode(
                        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
                    )

                    # 验证 token 类型
                    if payload.get("type") != "access":
                        raise HTTPException(
                            status_code=401, detail="Invalid token type"
                        )

                    # 从 payload 中获取用户 ID
                    user_id = payload.get("user_id")
                    if not user_id:
                        raise HTTPException(
                            status_code=401, detail="Invalid token - missing user ID"
                        )

                    # 将用户 ID 存储到上下文变量中
                    set_current_user_id(user_id)

                except jwt.ExpiredSignatureError:
                    # Token 过期
                    raise HTTPException(status_code=401, detail="Token expired")
                except jwt.InvalidTokenError:
                    # Token 无效
                    raise HTTPException(status_code=401, detail="Invalid token")

            # 不需要登录的路径，并且没有用户 ID， 抛出 401 错误
            none_auth_paths = ["/health", "/user/sms-code", "/user/login"]
            current_user_id = get_current_user_id()
            if current_user_id is None and request.url.path not in none_auth_paths:
                raise HTTPException(
                    status_code=401, detail="User ID not found in context"
                )

            # 继续处理请求
            response = await call_next(request)
            return response

        finally:
            # 清理用户 ID
            reset_current_user_id()
