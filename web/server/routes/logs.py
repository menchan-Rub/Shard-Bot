from fastapi import APIRouter, Depends
from web.server.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/")
async def get_logs(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "logs": [
                {
                    "timestamp": "2024-02-27T12:00:00Z",
                    "level": "INFO",
                    "message": "Bot started successfully"
                }
            ]
        }
    } 