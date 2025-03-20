from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import aiohttp
import asyncio
import time
import redis
import json
import logging
from functools import wraps

from database import get_db
from models import Guild, User, Command, Message
from schemas import StatsOverview, AnalyticsData, GuildStats
from routes.auth import get_current_user
from config import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])

DISCORD_API_URL = "https://discord.com/api/v10"
CACHE_TTL = 300  # 5分間のキャッシュ
DISCORD_RATE_LIMIT_COOLDOWN = 5  # 5秒のクールダウン

# Redis接続設定
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5
    )
    # 接続テスト
    redis_client.ping()
    REDIS_AVAILABLE = True
    logging.info("Redis接続を確立しました")
except Exception as e:
    REDIS_AVAILABLE = False
    logging.warning(f"Redis接続に失敗しました: {e}")
    logging.warning("メモリキャッシュに戻ります")

# メモリキャッシュのフォールバック
memory_cache = {}

# キャッシュ取得関数
def get_cache(key: str) -> Optional[Any]:
    if REDIS_AVAILABLE:
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logging.warning(f"Redisからの取得に失敗: {e}")
    
    # Redisが使えないかエラーの場合はメモリキャッシュを使用
    return memory_cache.get(key)

# キャッシュ保存関数
def set_cache(key: str, data: Any, ttl: int = CACHE_TTL) -> bool:
    if REDIS_AVAILABLE:
        try:
            redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logging.warning(f"Redisへの保存に失敗: {e}")
    
    # Redisが使えないかエラーの場合はメモリキャッシュに保存
    memory_cache[key] = data
    return True

# キャッシュクリア関数
def clear_cache(pattern: str = "*") -> bool:
    if REDIS_AVAILABLE:
        try:
            for key in redis_client.keys(pattern):
                redis_client.delete(key)
            return True
        except Exception as e:
            logging.warning(f"Redisキャッシュクリアに失敗: {e}")
    
    # メモリキャッシュをクリア
    if pattern == "*":
        memory_cache.clear()
    else:
        for key in list(memory_cache.keys()):
            if pattern.replace("*", "") in key:
                del memory_cache[key]
    return True

# キャッシングデコレータ
def cache_response(ttl: int = CACHE_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            # 関数名と引数に基づいてキーを作成
            key_parts = [func.__name__]
            
            # リクエストオブジェクトがあれば、URLとクエリパラメータを考慮
            for arg in args:
                if isinstance(arg, Request):
                    key_parts.append(str(arg.url))
                    break
            
            # その他の引数を追加
            for k, v in kwargs.items():
                if k != 'db' and k != 'current_user':
                    key_parts.append(f"{k}:{v}")
            
            # ユーザーIDも追加（ユーザー固有のキャッシュ）
            if 'current_user' in kwargs and hasattr(kwargs['current_user'], 'id'):
                key_parts.append(f"user:{kwargs['current_user'].id}")
            
            cache_key = "analytics:" + ":".join(map(str, key_parts))
            
            # キャッシュチェック
            cached_data = get_cache(cache_key)
            
            response = None
            if isinstance(args[1], Response):
                response = args[1]
            
            if cached_data:
                if response:
                    response.headers["X-Cache"] = "HIT"
                return cached_data
            
            # キャッシュがない場合は関数を実行
            result = await func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            set_cache(cache_key, result, ttl)
            
            if response:
                response.headers["X-Cache"] = "MISS"
            
            return result
        return wrapper
    return decorator

async def fetch_discord_data(token: str, retries: int = 2):
    """Discordから実際のデータを取得"""
    retry_count = 0
    last_error = None
    
    while retry_count <= retries:
        try:
            async with aiohttp.ClientSession() as session:
                # ユーザーの所属するサーバー一覧を取得
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                # ユーザーのサーバー一覧を取得
                async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=headers) as response:
                    # レート制限ヘッダーの処理
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', DISCORD_RATE_LIMIT_COOLDOWN))
                        logging.warning(f"Discord API レート制限: {retry_after}秒後に再試行します")
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    
                    if response.status != 200:
                        last_error = f"Discordサーバー情報の取得に失敗しました: ステータスコード {response.status}"
                        logging.error(last_error)
                        retry_count += 1
                        await asyncio.sleep(DISCORD_RATE_LIMIT_COOLDOWN)
                        continue
                        
                    user_guilds = await response.json()
                    
                # Botのサーバー一覧を取得
                bot_headers = {
                    "Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
                
                # キャッシュキー
                bot_guilds_cache_key = "discord:bot_guilds"
                bot_guilds = get_cache(bot_guilds_cache_key)
                
                if not bot_guilds:
                    async with session.get(f"{DISCORD_API_URL}/users/@me/guilds", headers=bot_headers) as response:
                        # レート制限ヘッダーの処理
                        if response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', DISCORD_RATE_LIMIT_COOLDOWN))
                            logging.warning(f"Discord API レート制限: {retry_after}秒後に再試行します")
                            await asyncio.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        if response.status != 200:
                            last_error = f"Bot情報の取得に失敗しました: ステータスコード {response.status}"
                            logging.error(last_error)
                            retry_count += 1
                            await asyncio.sleep(DISCORD_RATE_LIMIT_COOLDOWN)
                            continue
                            
                        bot_guilds = await response.json()
                        # 長めにキャッシュ（Botのギルドはそう頻繁に変わらない）
                        set_cache(bot_guilds_cache_key, bot_guilds, 3600)  # 1時間キャッシュ
                
                bot_guild_ids = {g["id"] for g in bot_guilds}
                
                # 管理者権限を持ち、かつBotが導入されているサーバーをフィルタリング
                admin_permission = 0x8  # ADMINISTRATOR permission
                filtered_guilds = [
                    guild for guild in user_guilds
                    if (int(guild["permissions"]) & admin_permission) == admin_permission  # 管理者権限チェック
                    or guild["owner"] == True  # オーナーチェック
                    and guild["id"] in bot_guild_ids  # Botが導入されているかチェック
                ]
                
                # 各サーバーの詳細情報を取得（並行処理で高速化）
                guild_detail_tasks = []
                for guild in filtered_guilds:
                    task = asyncio.create_task(fetch_guild_detail(session, bot_headers, guild["id"]))
                    guild_detail_tasks.append(task)
                
                guild_details = []
                for completed_task in asyncio.as_completed(guild_detail_tasks):
                    guild_data = await completed_task
                    if guild_data:
                        guild_details.append(guild_data)
                
                return {
                    "guilds": guild_details,
                    "total_servers": len(guild_details)
                }
                
        except Exception as e:
            last_error = str(e)
            logging.error(f"Discord APIエラー: {last_error}")
            retry_count += 1
            if retry_count <= retries:
                # 指数バックオフ
                await asyncio.sleep(DISCORD_RATE_LIMIT_COOLDOWN * (2 ** retry_count))
            else:
                break
    
    # すべてのリトライが失敗した場合
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Discordデータの取得に失敗しました: {last_error}"
    )

async def fetch_guild_detail(session, headers, guild_id):
    """ギルド詳細情報を取得"""
    cache_key = f"discord:guild:{guild_id}"
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data
    
    retry_count = 0
    max_retries = 2
    
    while retry_count <= max_retries:
        try:
            async with session.get(
                f"{DISCORD_API_URL}/guilds/{guild_id}?with_counts=true", 
                headers=headers
            ) as response:
                # レート制限ヘッダーの処理
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', DISCORD_RATE_LIMIT_COOLDOWN))
                    logging.warning(f"Guild {guild_id} レート制限: {retry_after}秒後に再試行")
                    await asyncio.sleep(retry_after)
                    retry_count += 1
                    continue
                
                if response.status == 200:
                    guild_data = await response.json()
                    result = {
                        "id": guild_data["id"],
                        "name": guild_data["name"],
                        "icon": guild_data.get("icon"),
                        "member_count": guild_data.get("approximate_member_count", 0),
                        "owner_id": guild_data["owner_id"]
                    }
                    # 1時間キャッシュ
                    set_cache(cache_key, result, 3600)
                    return result
                
                # 404などの場合は空を返す
                logging.warning(f"Guild {guild_id} の詳細取得に失敗: ステータス {response.status}")
                return None
        
        except Exception as e:
            logging.error(f"Guild {guild_id} 取得エラー: {str(e)}")
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(1 * retry_count)  # 簡易バックオフ
            else:
                return None

@router.get("/overview", response_model=StatsOverview)
@cache_response(ttl=300)  # 5分キャッシュ
async def get_stats_overview(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """統計概要を取得"""
    try:
        logging.info("統計概要の取得を開始")
        
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
        
        # 前週比の計算
        last_week = datetime.utcnow() - timedelta(days=7)
        commands_last_week = db.query(func.count(Command.id))\
            .filter(Command.created_at >= last_week)\
            .scalar() or 0
        
        users_last_week = db.query(func.count(func.distinct(Message.user_id)))\
            .filter(Message.created_at >= last_week)\
            .scalar() or 0
            
        result = {
            "total_servers": discord_data["total_servers"],
            "total_users": total_users,
            "total_commands": total_commands,
            "commands_today": commands_today,
            "new_users_today": new_users_today,
            "active_servers": active_servers,
            "weekly_command_count": commands_last_week,
            "weekly_active_users": users_last_week,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logging.info("統計概要の取得結果: %s", result)
        return result
        
    except Exception as e:
        logging.error("統計概要の取得でエラー発生: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計データの取得に失敗しました: {str(e)}"
        )

@router.get("/", response_model=List[AnalyticsData])
@cache_response(ttl=300)  # 5分キャッシュ
async def get_analytics_data(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=30, ge=1, le=90)
):
    """期間別の分析データを取得"""
    try:
        logging.info("分析データの取得を開始: %s日間", days)
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
            
        logging.info("分析データの取得完了: %s件のデータ", len(analytics_data))
        return analytics_data
        
    except Exception as e:
        logging.error("分析データの取得でエラー発生: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析データの取得に失敗しました: {str(e)}"
        )

@router.get("/server/{guild_id}/stats")
@cache_response(ttl=300)  # 5分キャッシュ
async def get_server_stats(
    guild_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=30)
):
    """サーバーごとの詳細統計を取得"""
    try:
        logging.info("サーバー %s の統計情報を取得開始: %s日間", guild_id, days)
        
        # 期間の設定
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # サーバーの存在確認（DBにない場合はDiscord APIから直接取得）
        guild = db.query(Guild).filter(Guild.discord_id == guild_id).first()
        if not guild:
            logging.info("データベースにサーバー %s が見つからないため、Discord APIから取得します", guild_id)
            
        # メンバー数の推移 (データがない場合はダミーデータ)
        member_stats = []
        
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
        
        # アクティブチャンネル
        active_channels = db.query(
            Message.channel_id,
            func.count(Message.id).label('count')
        )\
        .filter(
            Message.guild_id == guild_id,
            Message.created_at >= start_date
        )\
        .group_by(Message.channel_id)\
        .order_by(func.count(Message.id).desc())\
        .limit(5)\
        .all()
        
        # 日別アクティビティを補完（データがない日は0を設定）
        complete_daily_activity = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            activity = next(
                (act for act in daily_activity if act.date == current_date),
                None
            )
            
            if activity:
                complete_daily_activity.append({
                    "date": activity.date.strftime("%Y-%m-%d"),
                    "messages": activity.messages,
                    "users": activity.users
                })
            else:
                complete_daily_activity.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "messages": 0,
                    "users": 0
                })
            
            current_date += timedelta(days=1)
        
        # Discordから最新のサーバー情報を取得
        async with aiohttp.ClientSession() as session:
            bot_headers = {
                "Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            
            guild_info = await fetch_guild_detail(session, bot_headers, guild_id)
            if not guild_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="サーバーが見つかりません"
                )
        
        result = {
            "guild_info": guild_info,
            "stats": {
                "message_count": message_count,
                "active_users": active_users,
                "top_commands": [
                    {"name": cmd.name, "count": cmd.count}
                    for cmd in command_stats
                ],
                "daily_activity": complete_daily_activity,
                "active_channels": [
                    {"channel_id": str(channel.channel_id), "message_count": channel.count}
                    for channel in active_channels
                ]
            }
        }
        
        logging.info("サーバー %s の統計情報の取得完了", guild_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"サーバー統計の取得でエラー発生: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サーバー統計の取得に失敗しました: {str(e)}"
        )

@router.get("/guild/{guild_id}", response_model=GuildStats)
@cache_response(ttl=300)  # 5分キャッシュ
async def get_guild_stats(
    guild_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=30)
):
    """特定のサーバーの統計情報を取得"""
    # 下位互換性のため同じ機能を異なるエンドポイントで提供
    return await get_server_stats(guild_id, request, response, db, current_user, days)

@router.get("/invalidate-cache")
async def invalidate_analytics_cache(
    current_user: User = Depends(get_current_user),
    pattern: str = "*"
):
    """分析データのキャッシュを無効化（管理者用）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です"
        )
    
    cache_key = f"analytics:{pattern}"
    success = clear_cache(cache_key)
    
    return {
        "status": "success" if success else "error",
        "message": f"キャッシュを無効化しました: {cache_key}" if success else "キャッシュの無効化に失敗しました"
    } 