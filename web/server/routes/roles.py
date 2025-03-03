from fastapi import APIRouter, Depends
from web.server.routes.auth import get_current_user

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("/")
async def get_roles(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "roles": [
                {
                    "id": "1",
                    "name": "Admin",
                    "permissions": ["read", "write", "delete"]
                }
            ]
        }
    }

@router.get("/{role_id}")
async def get_role(role_id: str, current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "role": {
                "id": role_id,
                "name": "Moderator",
                "color": "#00FF00",
                "permissions": ["MANAGE_MESSAGES", "KICK_MEMBERS"]
            }
        }
    } 