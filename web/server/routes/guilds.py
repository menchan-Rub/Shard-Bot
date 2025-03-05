from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import aiohttp

from ..database import get_db
from ..models import User
from ..schemas.guilds import GuildList
from .auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/guilds", tags=["guilds"])

DISCORD_API_URL = "https://discord.com/api/v10"

@router.get("/", response_model=GuildList)
async def get_guilds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ユーザーが所属するDiscordサーバー一覧を取得"""
    try:
        # 開発用のダミーデータを返す
        dummy_guilds = [
            {
                "id": "123456789",
                "name": "テストサーバー1",
                "icon": None,
                "owner": True,
                "permissions": "8"  # 管理者権限
            },
            {
                "id": "987654321",
                "name": "テストサーバー2",
                "icon": None,
                "owner": True,
                "permissions": "8"
            },
            {
                "id": "456789123",
                "name": "開発用サーバー",
                "icon": None,
                "owner": True,
                "permissions": "8"
            }
        ]
        
        return {
            "guilds": dummy_guilds
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予期せぬエラーが発生しました: {str(e)}"
        ) 