

from pydantic import BaseModel, Field


class SMSCodeRequest(BaseModel):
    """发送短信验证码请求"""
    email: str = Field(..., description="邮箱")

class LoginRequest(BaseModel):
    """注册用户请求"""
    email: str = Field(..., description="邮箱")
    code: str = Field(..., description="邮箱验证码")


class InfoResponse(BaseModel):
    """用户用户信息响应"""
    email: str = Field(..., description="邮箱")
    name: str = Field(..., description="用户名")
    created_at: int = Field(..., description="创建时间")