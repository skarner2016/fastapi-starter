from app.api.user_api import user_router
from app.core.response import ApiResponseSuccess
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
def health_check():
    return ApiResponseSuccess(data={"status": "ok"})

api_router.include_router(user_router)