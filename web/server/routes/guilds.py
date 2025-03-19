from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import aiohttp
import logging

from database import get_db
from models import User
from schemas.guilds import GuildList
from routes.auth import get_current_user
from config import settings

router = APIRouter(prefix="/guilds", tags=["guilds"])

DISCORD_API_URL = "https://discord.com/api/v10"
logger = logging.getLogger(__name__)

@router.get("/", response_model=GuildList)
async def get_guilds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ユーザーが所属するDiscordサーバー一覧を取得"""
    try:
        # Discord APIからユーザーのサーバー一覧を取得
        if not current_user.discord_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Discord認証情報が見つかりません。再ログインしてください。"
            )
        
        # 1. ユーザーが所属するサーバーを取得
        user_guilds = await fetch_user_guilds(current_user.discord_access_token)
        
        # 2. Botが所属するサーバーを取得
        bot_guilds = await fetch_bot_guilds(settings.DISCORD_BOT_TOKEN)
        
        # 3. ユーザーが管理者権限を持ち、かつBotが入室しているサーバーをフィルタリング
        filtered_guilds = filter_guilds(user_guilds, bot_guilds)
        
        return {
            "guilds": filtered_guilds
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サーバー一覧取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予期せぬエラーが発生しました: {str(e)}"
        )

async def fetch_user_guilds(access_token: str):
    """Discord APIからユーザーのサーバー一覧を取得"""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Discord API エラー (ユーザーギルド): {await response.text()}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Discord APIとの通信に失敗しました"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Discord API 接続エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discord APIに接続できませんでした"
        )

async def fetch_bot_guilds(bot_token: str):
    """Discord APIからBotのサーバー一覧を取得"""
    headers = {
        "Authorization": f"Bot {bot_token}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Discord API エラー (Botギルド): {await response.text()}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Discord Bot APIとの通信に失敗しました"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Discord Bot API 接続エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discord Bot APIに接続できませんでした"
        )

def filter_guilds(user_guilds, bot_guilds):
    """
    ユーザーが管理者権限を持ち、かつBotが入室しているサーバーをフィルタリング
    管理者権限: permissions値を整数に変換し、0x8 (ADMINISTRATOR) フラグが立っているか確認
    """
    # Botが参加しているサーバーIDのセットを作成
    bot_guild_ids = {guild["id"] for guild in bot_guilds}
    
    # ユーザーの権限をチェック
    filtered = []
    for guild in user_guilds:
        # 数値としての権限値を取得
        permissions = int(guild.get("permissions", "0"))
        
        # 0x8 は ADMINISTRATOR フラグ
        is_admin = (permissions & 0x8) == 0x8 or guild.get("owner", False)
        
        # Botが参加していて、かつユーザーが管理者権限を持っている場合のみ追加
        if guild["id"] in bot_guild_ids and is_admin:
            filtered.append(guild)
    
    return filtered 