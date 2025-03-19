from fastapi import Request, Response, status
import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from typing import Union, Dict, Any

# ロガーの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def handle_errors(request: Request, call_next):
    """アプリケーション全体のエラーハンドラーミドルウェア"""
    try:
        logger.debug(f"Processing request: {request.method} {request.url}")
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Exception during request: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # エラーメッセージを構築
        error_detail = str(e)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # 標準レスポンスを作成
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "detail": error_detail,
                "type": type(e).__name__
            }
        )

class APIError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Union[Dict[str, Any], None] = None
    ):
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message) 