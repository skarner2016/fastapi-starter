import time
from app.core import utils
from app.core.context import get_redis_pool, get_mysql_pool, get_current_user_id
from app.core.response import ApiResponseFail, ApiResponseSuccess
from app.models.user_model import UserModel
from sqlalchemy import select
from app.schemas.user_schema import SMSCodeRequest, LoginRequest, InfoResponse
from fastapi import APIRouter, Request
from app.core.utils import generate_jwt_token
from app.core import get_logger

user_router = APIRouter(prefix="/user", tags=["user"])

logger = get_logger()


@user_router.post("/sms-code")
async def sms_code(request: SMSCodeRequest):
    """发送短信验证码"""
    code = utils.generate_6_digit_code()
    redis_conn = get_redis_pool()
    await redis_conn.set(request.email, code, ex=600)

    return ApiResponseSuccess(data={"code": code})


@user_router.post("/login")
async def login(request: LoginRequest):
    """用户注册&登录系统"""
    email = request.email
    code = request.code

    redis_conn = get_redis_pool()
    cached_code = await redis_conn.get(email)
    if cached_code is None:
        return ApiResponseFail(message="验证码过期或不存在")

    if cached_code != code:
        return ApiResponseFail(message="验证码错误")    

    # 判断 email 是否一已注册
    mysql_pool = get_mysql_pool()
    result = await mysql_pool.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # 用户未注册，创建新用户
        user = UserModel(
            email=email, name=email.split("@")[0], created_at=int(time.time())
        )
        mysql_pool.add(user)
        await mysql_pool.flush()
        await mysql_pool.refresh(user)

    # 生成 jwt_token
    jwt_token = generate_jwt_token(user.id, user.name, user.email)
    await redis_conn.delete(email)

    # 登录系统，返回 jwt_token
    return ApiResponseSuccess(data={"jwt_token": jwt_token, "token_type": "Bearer"})


@user_router.post("/info")
async def info(request: Request):
    """用户用户信息"""

    user_id = get_current_user_id()
    if not user_id:
        return ApiResponseFail(message="未登录或Token无效")

    # 从数据库查询用户信息
    result = await get_mysql_pool().execute(
        select(UserModel).where(UserModel.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        return ApiResponseFail(message="用户不存在")

    return ApiResponseSuccess(  
        data=InfoResponse(
            email=user.email, name=user.name, created_at=user.created_at
        ).model_dump(),
    )
