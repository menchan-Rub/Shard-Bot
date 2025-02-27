from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Union, Dict, Any

async def handle_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "code": getattr(e, "code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        }
        
        return JSONResponse(
            status_code=error_response["code"],
            content=error_response
        )

class APIError(Exception):
    def __init__(
        self,
        message: str,
        code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Union[Dict[str, Any], None] = None
    ):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message) 