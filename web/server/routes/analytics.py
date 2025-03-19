from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import aiohttp

from database import get_db
from models import Guild, User, Command, Message
from schemas import StatsOverview, AnalyticsData, GuildStats
from routes.auth import get_current_user
from config import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])

DISCORD_API_URL = "https://discord.com/api/v10"

async def fetch_discord_data(token: str):
    """Discordから実際のデータを取得"""
    async with aiohttp.ClientSession() as session:
        # ユーザーの所属するサーバー一覧を取得
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # ユーザーのサーバー一覧を取得
            async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=headers) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Discordサーバー情報の取得に失敗しました"
                    )
                user_guilds = await response.json()
                
            # Botのサーバー一覧を取得
            bot_headers = {
                "Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=bot_headers) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Bot情報の取得に失敗しました"
                    )
                bot_guilds = await response.json()
                bot_guild_ids = {g["id"] for g in bot_guilds}
                
            # 管理者権限を持ち、かつBotが導入されているサーバーをフィルタリング
            admin_permission = 0x8  # ADMINISTRATOR permission
            filtered_guilds = [
                guild for guild in user_guilds
                if (int(guild["permissions"]) & admin_permission) == admin_permission  # 管理者権限チェック
                and guild["id"] in bot_guild_ids  # Botが導入されているかチェック
            ]
            
            # 各サーバーの詳細情報を取得
            guild_details = []
            for guild in filtered_guilds:
                async with session.get(
                    f"{DISCORD_API_URL}/guilds/{guild['id']}", 
                    headers=bot_headers
                ) as response:
                    if response.status == 200:
                        guild_data = await response.json()
                        guild_details.append({
                            "id": guild_data["id"],
                            "name": guild_data["name"],
                            "icon": guild_data.get("icon"),
                            "member_count": guild_data.get("approximate_member_count", 0),
                            "owner_id": guild_data["owner_id"]
                        })
                        
            return {
                "guilds": guild_details,
                "total_servers": len(guild_details)
            }
            
        except Exception as e:
            print(f"Discord APIエラー: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Discordデータの取得に失敗しました: {str(e)}"
            )

@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """統計概要を取得"""
    try:
        print("統計概要の取得を開始")
        
        # Discordから実際のデータを取得
        discord_data = await fetch_discord_data(current_user.discord_access_token)
        
        # データベースの統計情報を取得
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_commands = db.query(func.count(Command.id)).scalar() or 0
        
        # 今日の統計
        today = datetime.utcnow().date()
        commands_today = db.query(func.count(Command.id))\
            .filter(func.date(Command.created_at) == today)\
            .scalar() or 0
            
        new_users_today = db.query(func.count(User.id))\
            .filter(func.date(User.created_at) == today)\
            .scalar() or 0
            
        # アクティブサーバーの定義を変更（24時間以内にメッセージがあったサーバー）
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_servers = db.query(func.count(func.distinct(Message.guild_id)))\
            .filter(Message.created_at >= yesterday)\
            .scalar() or 0
            
        result = {
            "total_servers": discord_data["total_servers"],
            "total_users": total_users,
            "total_commands": total_commands,
            "commands_today": commands_today,
            "new_users_today": new_users_today,
            "active_servers": active_servers
        }
        
        print("統計概要の取得結果:", result)
        return result
        
    except Exception as e:
        print("統計概要の取得でエラー発生:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計データの取得に失敗しました: {str(e)}"
        )

@router.get("/", response_model=List[AnalyticsData])
async def get_analytics_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """期間別の分析データを取得"""
    try:
        print("分析データの取得を開始")
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # コマンド実行統計
        command_stats = db.query(
            func.date(Command.created_at).label('date'),
            func.count(Command.id).label('count')
        )\
        .filter(Command.created_at >= start_date)\
        .group_by(func.date(Command.created_at))\
        .all()
        
        # アクティブユーザー統計
        user_stats = db.query(
            func.date(Message.created_at).label('date'),
            func.count(func.distinct(Message.user_id)).label('count')
        )\
        .filter(Message.created_at >= start_date)\
        .group_by(func.date(Message.created_at))\
        .all()
        
        # データを結合
        analytics_data = []
        current_date = start_date
        
        while current_date <= end_date:
            command_count = next(
                (stat.count for stat in command_stats if stat.date == current_date),
                0
            )
            user_count = next(
                (stat.count for stat in user_stats if stat.date == current_date),
                0
            )
            
            analytics_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "commands": command_count,
                "users": user_count
            })
            
            current_date += timedelta(days=1)
            
        print("分析データの取得結果:", analytics_data[:5])  # 最初の5件のみ表示
        return analytics_data
        
    except Exception as e:
        print("分析データの取得でエラー発生:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析データの取得に失敗しました: {str(e)}"
        )

@router.get("/server/{guild_id}/stats")
async def get_server_stats(
    guild_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """サーバーごとの詳細統計を取得"""
    try:
        # サーバーの存在確認
        guild = db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="サーバーが見つかりません"
            )
            
        # メンバー数の推移
        member_stats = db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        )\
        .filter(User.guild_id == guild_id)\
        .group_by(func.date(User.created_at))\
        .all()
        
        # コマンド使用統計
        command_stats = db.query(
            Command.name,
            func.count(Command.id).label('count')
        )\
        .filter(Command.guild_id == guild_id)\
        .group_by(Command.name)\
        .order_by(func.count(Command.id).desc())\
        .limit(10)\
        .all()
        
        # アクティブチャンネル
        active_channels = db.query(
            Message.channel_id,
            func.count(Message.id).label('count')
        )\
        .filter(Message.guild_id == guild_id)\
        .group_by(Message.channel_id)\
        .order_by(func.count(Message.id).desc())\
        .limit(5)\
        .all()
        
        return {
            "member_stats": [
                {"date": stat.date.strftime("%Y-%m-%d"), "count": stat.count}
                for stat in member_stats
            ],
            "command_stats": [
                {"name": stat.name, "count": stat.count}
                for stat in command_stats
            ],
            "active_channels": [
                {"channel_id": stat.channel_id, "message_count": stat.count}
                for stat in active_channels
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバー統計の取得に失敗しました"
        )

@router.get("/guild/{guild_id}", response_model=GuildStats)
async def get_guild_stats(
    guild_id: str,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """特定のサーバーの統計情報を取得"""
    try:
        print(f"サーバー {guild_id} の統計情報を取得中")
        
        # 期間の設定
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # コマンド使用統計
        command_stats = db.query(
            Command.name,
            func.count(Command.id).label('count')
        )\
        .filter(
            Command.guild_id == guild_id,
            Command.created_at >= start_date
        )\
        .group_by(Command.name)\
        .order_by(func.count(Command.id).desc())\
        .limit(10)\
        .all()
        
        # メッセージ統計
        message_count = db.query(func.count(Message.id))\
            .filter(
                Message.guild_id == guild_id,
                Message.created_at >= start_date
            )\
            .scalar() or 0
            
        # アクティブユーザー数
        active_users = db.query(func.count(func.distinct(Message.user_id)))\
            .filter(
                Message.guild_id == guild_id,
                Message.created_at >= start_date
            )\
            .scalar() or 0
            
        # 日別のアクティビティ
        daily_activity = db.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('messages'),
            func.count(func.distinct(Message.user_id)).label('users')
        )\
        .filter(
            Message.guild_id == guild_id,
            Message.created_at >= start_date
        )\
        .group_by(func.date(Message.created_at))\
        .order_by(func.date(Message.created_at))\
        .all()
        
        # Discordから最新のサーバー情報を取得
        bot_headers = {
            "Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DISCORD_API_URL}/guilds/{guild_id}",
                headers=bot_headers
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="サーバーが見つかりません"
                    )
                guild_data = await response.json()
        
        return {
            "guild_info": {
                "id": guild_data["id"],
                "name": guild_data["name"],
                "icon": guild_data.get("icon"),
                "member_count": guild_data.get("approximate_member_count", 0),
                "owner_id": guild_data["owner_id"]
            },
            "stats": {
                "message_count": message_count,
                "active_users": active_users,
                "top_commands": [
                    {"name": cmd.name, "count": cmd.count}
                    for cmd in command_stats
                ],
                "daily_activity": [
                    {
                        "date": activity.date.strftime("%Y-%m-%d"),
                        "messages": activity.messages,
                        "users": activity.users
                    }
                    for activity in daily_activity
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"サーバー統計の取得でエラー発生: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サーバー統計の取得に失敗しました: {str(e)}"
        ) 