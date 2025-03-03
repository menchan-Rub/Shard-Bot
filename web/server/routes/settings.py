from fastapi import APIRouter, Depends
from web.server.routes.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
async def get_settings(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "settings": {
                "notifications": True,
                "theme": "dark",
                "language": "ja"
            }
        }
    } 