from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import aiohttp

from ..database import get_db
from ..models import User
from ..schemas.roles import RoleResponse, RoleList
from .auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/roles", tags=["roles"])

DISCORD_API_URL = "https://discord.com/api/v10"

@router.get("/", response_model=RoleList)
async def get_roles(
    guild_id: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """サーバーのロール一覧を取得"""
    try:
        # 開発用のダミーデータ
        dummy_roles = [
            {
                "id": "111111111",
                "name": "@everyone",
                "color": "#99AAB5",
                "hoist": False,
                "position": 0,
                "permissions": "0",
                "mentionable": False,
                "member_count": 10
            },
            {
                "id": "222222222",
                "name": "管理者",
                "color": "#FF0000",
                "hoist": True,
                "position": 5,
                "permissions": "8",
                "mentionable": True,
                "member_count": 2
            },
            {
                "id": "333333333",
                "name": "モデレーター",
                "color": "#00FF00",
                "hoist": True,
                "position": 4,
                "permissions": "4",
                "mentionable": True,
                "member_count": 5
            },
            {
                "id": "444444444",
                "name": "メンバー",
                "color": "#0000FF",
                "hoist": False,
                "position": 1,
                "permissions": "0",
                "mentionable": False,
                "member_count": 8
            }
        ]

        # ページネーション
        start = (page - 1) * limit
        end = start + limit
        paginated_roles = dummy_roles[start:end]

        return {
            "roles": paginated_roles,
            "total": len(dummy_roles),
            "page": page,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予期せぬエラーが発生しました: {str(e)}"
        )

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