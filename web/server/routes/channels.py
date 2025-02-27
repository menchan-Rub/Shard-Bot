from fastapi import APIRouter, Depends
from web.server.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/channels", tags=["channels"])

@router.get("/")
async def get_channels(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "channels": [
                {
                    "id": "123456789",
                    "name": "general",
                    "type": "text",
                    "position": 0
                }
            ]
        }
    }

@router.get("/{channel_id}")
async def get_channel(channel_id: str, current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "channel": {
                "id": channel_id,
                "name": "announcements",
                "type": "text",
                "position": 1,
                "topic": "Important announcements"
            }
        }
    } 