from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Union, Dict, Any

async def handle_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_response = {
            "status": "error",
            "detail": str(e),
        }
        
        # ステータスコードの設定
        status_code = getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not isinstance(status_code, int):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
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