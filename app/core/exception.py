import traceback

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.logging import get_logger
from app.schemas.error_code import ErrorCode


class ApiBusinessException(Exception):
    def __init__(self, code: int = 500, message: str = "", status_code: int = status.HTTP_200_OK):
        self.code = code  # 业务错误码（如 1001、1002，区分不同业务场景）
        self.message = message  # 错误描述
        self.status_code = status_code  # HTTP 状态码（默认 400 Bad Request）
        super().__init__(self.message)


async def api_business_exception_handler(request: Request, exc: ApiBusinessException):
    # 返回标准化的 JSON 响应
    error_msg = exc.message
    if not error_msg:
        error_msg = ErrorCode().get_error_msg(exc.code)

    return JSONResponse(
        content={"code": exc.code, "message": error_msg, "data": {}}, status_code=status.HTTP_200_OK
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    # 获取所有错误列表
    all_errors = exc.errors()
    # 取第一条错误
    first_error = all_errors[0] if all_errors else {}
    # 提取第一条错误的信息（msg）和位置（loc）
    first_error_msg = first_error.get("msg", "Unknown error")
    first_error_loc = first_error.get("loc", ())  # loc表示错误位置，如["body", "price"]

    field_parts = [str(part) for part in first_error_loc[1:]]  # 跳过位置标识（如 'body'）
    first_field = ".".join(field_parts) if field_parts else "unknown field"

    message = first_field + ":" + first_error_msg

    # 业务状态码返回500
    return JSONResponse(
        content={"code": ErrorCode.VALIDATION, "message": message, "data": {}}, status_code=status.HTTP_200_OK
    )


async def global_exception_handler(request: Request, exc: Exception):
    # 日志
    get_logger().error(f"【global_exception_handler】{exc}\n{traceback.format_exc()}")

    # 返回统一格式
    return JSONResponse(
        content={"code": ErrorCode.UNKNOWN, "message": "Unknown error", "data": {}}, status_code=status.HTTP_200_OK
    )


def register_exceptions(app: FastAPI) -> None:
    """
    异常捕捉, http状态码统一用200， 通过业务状态码来判断
    """
    # 业务异常
    app.add_exception_handler(ApiBusinessException, api_business_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)

    @app.middleware("http")
    async def catch_all_exceptions(request: Request, call_next):
        try:
            return await call_next(request)

        # 捕获所有代码异常：raise Exception(...)
        except Exception as exc:
            # 记录日志
            get_logger().error(f"【catch_all_exceptions】{exc}\n{traceback.format_exc()}")

            # 返回统一格式
            return JSONResponse(
                content={"code": ErrorCode.UNKNOWN, "message": "Unknown error", "data": {}},
                status_code=status.HTTP_200_OK
            )