from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

# 定义一个类型变量，用于泛型（表示 data 字段的具体类型）
DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    code: int = 0
    message: str = "success"
    data: Optional[DataT] = {}  # 业务数据（泛型，支持任意 JSON 结构）

class ApiResponseSuccess(ApiResponse):
    code: int = 0
    message: str = "success"

class ApiResponseFail(ApiResponse):
    code: int = -1
    message: str = "error"