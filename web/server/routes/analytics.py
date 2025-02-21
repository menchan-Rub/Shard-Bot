from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Guild, User, Command, Message
from ..schemas import StatsOverview, AnalyticsData
from .auth import get_current_user

router = APIRouter()

@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """統計概要を取得"""
    try:
        # 基本統計
        total_servers = db.query(func.count(Guild.id)).scalar()
        total_users = db.query(func.count(User.id)).scalar()
        total_commands = db.query(func.count(Command.id)).scalar()
        
        # 今日の統計
        today = datetime.utcnow().date()
        commands_today = db.query(func.count(Command.id))\
            .filter(func.date(Command.created_at) == today)\
            .scalar()
            
        new_users_today = db.query(func.count(User.id))\
            .filter(func.date(User.created_at) == today)\
            .scalar()
            
        active_servers = db.query(func.count(Guild.id))\
            .filter(Guild.last_activity >= today)\
            .scalar()
            
        return {
            "total_servers": total_servers,
            "total_users": total_users,
            "total_commands": total_commands,
            "commands_today": commands_today,
            "new_users_today": new_users_today,
            "active_servers": active_servers
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="統計データの取得に失敗しました"
        )

@router.get("/analytics", response_model=List[AnalyticsData])
async def get_analytics_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """期間別の分析データを取得"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 日付ごとのコマンド実行数
        command_stats = db.query(
            func.date(Command.created_at).label('date'),
            func.count(Command.id).label('count')
        )\
        .filter(Command.created_at >= start_date)\
        .group_by(func.date(Command.created_at))\
        .all()
        
        # 日付ごとのアクティブユーザー数
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
            
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分析データの取得に失敗しました"
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