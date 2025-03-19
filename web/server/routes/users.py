from fastapi import APIRouter, Depends
from routes.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "user": current_user
        }
    }

@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "user": {
                "id": user_id,
                "username": "example_user",
                "discriminator": "1234",
                "avatar": "https://cdn.discordapp.com/avatars/123456789/abcdef.png"
            }
        }
    } 