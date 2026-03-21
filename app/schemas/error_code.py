from fastapi import status


class ErrorCode:
    # 系统状态码
    SUCCESS: int = 0
    UNKNOWN: int = -1
    VALIDATION: int = status.HTTP_422_UNPROCESSABLE_CONTENT

    # 业务状态码
    def get_error_msg(self, error_code=UNKNOWN) -> str:
        return f"error_code:{error_code}"
