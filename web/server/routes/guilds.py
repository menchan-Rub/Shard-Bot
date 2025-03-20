import asyncio
import json
import logging
import os
import time
from functools import wraps
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta

import aiohttp
import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

# ロガーのセットアップ
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# APIエンドポイント
DISCORD_API_BASE = "https://discord.com/api/v10"
USER_GUILDS_ENDPOINT = f"{DISCORD_API_BASE}/users/@me/guilds"
BOT_GUILDS_ENDPOINT = f"{DISCORD_API_BASE}/users/@me/guilds"

# Botトークン
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Discord Bot Tokenが設定されていません")

# Redis接続
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# キャッシュキーとTTL
USER_GUILDS_CACHE_KEY = "discord:user_guilds:{user_id}"
USER_GUILDS_CACHE_TTL = 60 * 15  # 15分
BOT_GUILDS_CACHE_KEY = "discord:bot_guilds"
BOT_GUILDS_CACHE_TTL = 60 * 30  # 30分

# レート制限関連の定数
MAX_RETRIES = 2
RATE_LIMIT_COOLDOWN = 5  # 秒
RATE_LIMIT_BACKOFF_MULTIPLIER = 2
DEFAULT_RETRY_AFTER = 5  # 秒

# 管理者権限フラグ (0x8)
ADMINISTRATOR = 0x8

router = APIRouter()

# Redis クライアントのシングルトンインスタンス
_redis_client = None

def get_redis_client():
    """Redis クライアントのシングルトンインスタンスを取得"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT, 
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                socket_timeout=5,
                decode_responses=True
            )
            # 接続テスト
            _redis_client.ping()
            logger.info("Redisに正常に接続しました")
        except redis.RedisError as e:
            logger.error(f"Redis接続エラー: {e}")
            _redis_client = None
    return _redis_client

# デコレータ: エンドポイントをキャッシュ用にラップ
def cache_endpoint(cache_key_fn, ttl):
    """エンドポイントの結果をキャッシュするデコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            cache_key = cache_key_fn(*args, **kwargs)
            response = Response()
            
            # Redisクライアントの取得
            redis_client = get_redis_client()
            
            # Redisが利用可能な場合はキャッシュチェック
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.debug(f"キャッシュヒット: {cache_key}")
                        response.headers["X-Cache"] = "HIT"
                        return json.loads(cached_data)
                except Exception as e:
                    logger.error(f"キャッシュ読み取りエラー: {e}")
            
            # キャッシュミスまたはRedisが利用不可の場合、元の関数を実行
            response.headers["X-Cache"] = "MISS"
            result = await func(*args, **kwargs)
            
            # 結果をキャッシュ（Redisが利用可能な場合）
            if redis_client and result:
                try:
                    redis_client.setex(
                        cache_key, 
                        ttl, 
                        json.dumps(result)
                    )
                    logger.debug(f"キャッシュ保存: {cache_key}, TTL: {ttl}秒")
                except Exception as e:
                    logger.error(f"キャッシュ保存エラー: {e}")
            
            return result
        return wrapper
    return decorator

# Discord APIへのリクエストを処理する関数
async def make_discord_request(
    url: str, 
    token: str, 
    is_bot: bool = False, 
    retries: int = MAX_RETRIES
) -> Tuple[Union[List[Dict], Dict, None], Optional[str], int]:
    """
    Discord APIにリクエストを送信し、レート制限を処理する
    
    Args:
        url: リクエスト先のURL
        token: アクセストークン
        is_bot: Botトークンかどうか
        retries: 最大リトライ回数
        
    Returns:
        (レスポンスデータ, エラーメッセージ, ステータスコード)
    """
    headers = {
        "Authorization": f"{'Bot' if is_bot else 'Bearer'} {token}",
        "Content-Type": "application/json"
    }
    
    retry_count = 0
    retry_after = 0
    
    while retry_count <= retries:
        # リトライの場合は待機
        if retry_after > 0:
            logger.info(f"レート制限のため{retry_after}秒待機中... (試行 {retry_count}/{retries})")
            await asyncio.sleep(retry_after)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    status = response.status
                    
                    # レート制限ヘッダの解析
                    remaining = int(response.headers.get("X-RateLimit-Remaining", "-1"))
                    reset_after = float(response.headers.get("X-RateLimit-Reset-After", "0"))
                    
                    logger.debug(f"Discord API レスポンス: {status}, 残りリクエスト: {remaining}, リセットまで: {reset_after}秒")
                    
                    # 成功
                    if 200 <= status < 300:
                        return await response.json(), None, status
                    
                    # レート制限 (429)
                    if status == 429:
                        retry_after = float(response.headers.get("Retry-After", DEFAULT_RETRY_AFTER))
                        # バックオフ係数を適用
                        retry_after = retry_after * (RATE_LIMIT_BACKOFF_MULTIPLIER ** retry_count)
                        retry_count += 1
                        logger.warning(f"Discord API レート制限: {retry_after}秒後にリトライします (試行 {retry_count})")
                        continue
                    
                    # その他のエラー
                    error_data = await response.text()
                    logger.error(f"Discord API エラー: {status} - {error_data}")
                    error_msg = f"Discord API エラー ({status})"
                    return None, error_msg, status
                    
        except aiohttp.ClientError as e:
            retry_count += 1
            retry_after = RATE_LIMIT_COOLDOWN * (RATE_LIMIT_BACKOFF_MULTIPLIER ** retry_count)
            logger.error(f"Discord API 接続エラー: {e}, {retry_after}秒後にリトライ (試行 {retry_count})")
            
            if retry_count > retries:
                return None, f"Discord API 接続エラー: {e}", 500
        
        except asyncio.TimeoutError:
            retry_count += 1
            retry_after = RATE_LIMIT_COOLDOWN * (RATE_LIMIT_BACKOFF_MULTIPLIER ** retry_count)
            logger.error(f"Discord API タイムアウト, {retry_after}秒後にリトライ (試行 {retry_count})")
            
            if retry_count > retries:
                return None, "Discord API タイムアウト", 504
        
        except Exception as e:
            logger.exception(f"予期しないエラー: {e}")
            return None, f"予期しないエラー: {e}", 500
    
    # 最大リトライ回数に達した
    return None, "最大リトライ回数に達しました", 429

# ユーザーのギルドを取得
async def fetch_user_guilds(user_id: str, access_token: str) -> Tuple[List[Dict], Optional[str], int]:
    """
    ユーザーが所属するギルドの一覧を取得
    
    Args:
        user_id: ユーザーID
        access_token: DiscordのAccess Token
        
    Returns:
        (ギルドリスト, エラーメッセージ, ステータスコード)
    """
    start_time = time.time()
    logger.info(f"ユーザー {user_id} のギルド取得を開始")
    
    # Redis キャッシュのチェック
    redis_client = get_redis_client()
    cache_key = USER_GUILDS_CACHE_KEY.format(user_id=user_id)
    
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info(f"ユーザー {user_id} のギルドをキャッシュから取得 (経過時間: {time.time() - start_time:.2f}秒)")
                return json.loads(cached_data), None, 200
        except Exception as e:
            logger.error(f"キャッシュ読み取りエラー: {e}")
    
    # Discord APIからデータ取得
    guilds_data, error_msg, status = await make_discord_request(USER_GUILDS_ENDPOINT, access_token)
    
    # エラー処理
    if error_msg or not guilds_data:
        logger.error(f"ユーザーギルド取得エラー: {error_msg}, ステータス: {status}")
        return [], error_msg, status
    
    # データ検証
    if not isinstance(guilds_data, list):
        logger.error(f"無効なユーザーギルドデータ: リストではありません - {type(guilds_data)}")
        return [], "無効なAPIレスポンス", 500
    
    # 管理者権限または所有者のみのギルドをフィルタリング
    admin_guilds = []
    for guild in guilds_data:
        try:
            # 必須フィールドの検証
            if not all(k in guild for k in ["id", "name", "permissions"]):
                logger.warning(f"不完全なギルドデータをスキップ: {guild}")
                continue
                
            # 権限の解析 (文字列または整数)
            permissions = int(guild["permissions"])
            is_admin = (permissions & ADMINISTRATOR) == ADMINISTRATOR
            is_owner = guild.get("owner", False)
            
            if is_admin or is_owner:
                # 返却に必要なフィールドのみ抽出
                admin_guilds.append({
                    "id": guild["id"],
                    "name": guild["name"],
                    "icon": guild.get("icon"),
                    "owner": guild.get("owner", False),
                    "permissions": guild["permissions"]
                })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"ギルドデータ処理エラー: {e}, データ: {guild}")
            continue
    
    # キャッシュに保存
    if redis_client and admin_guilds:
        try:
            redis_client.setex(
                cache_key, 
                USER_GUILDS_CACHE_TTL, 
                json.dumps(admin_guilds)
            )
            logger.debug(f"ユーザー {user_id} のギルドをキャッシュに保存 (TTL: {USER_GUILDS_CACHE_TTL}秒)")
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    logger.info(f"ユーザー {user_id} のギルド取得を完了: {len(admin_guilds)}件 (経過時間: {time.time() - start_time:.2f}秒)")
    return admin_guilds, None, 200

# ボットのギルドを取得
async def fetch_bot_guilds() -> Tuple[List[Dict], Optional[str], int]:
    """
    ボットが参加しているギルドの一覧を取得
    
    Returns:
        (ギルドリスト, エラーメッセージ, ステータスコード)
    """
    if not BOT_TOKEN:
        logger.error("Bot トークンが設定されていません")
        return [], "Bot トークンが設定されていません", 500
    
    start_time = time.time()
    logger.info("ボットのギルド取得を開始")
    
    # Redis キャッシュのチェック
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            cached_data = redis_client.get(BOT_GUILDS_CACHE_KEY)
            if cached_data:
                logger.info(f"ボットのギルドをキャッシュから取得 (経過時間: {time.time() - start_time:.2f}秒)")
                return json.loads(cached_data), None, 200
        except Exception as e:
            logger.error(f"キャッシュ読み取りエラー: {e}")
    
    # Discord APIからデータ取得
    guilds_data, error_msg, status = await make_discord_request(
        BOT_GUILDS_ENDPOINT, 
        BOT_TOKEN, 
        is_bot=True
    )
    
    # エラー処理
    if error_msg or not guilds_data:
        logger.error(f"ボットギルド取得エラー: {error_msg}, ステータス: {status}")
        return [], error_msg, status
    
    # データ検証
    if not isinstance(guilds_data, list):
        logger.error(f"無効なボットギルドデータ: リストではありません - {type(guilds_data)}")
        return [], "無効なAPIレスポンス", 500
    
    # IDのみの辞書リストに変換
    bot_guilds = []
    for guild in guilds_data:
        try:
            if "id" in guild:
                bot_guilds.append({"id": guild["id"]})
        except Exception as e:
            logger.warning(f"ボットギルドデータ処理エラー: {e}, データ: {guild}")
    
    # キャッシュに保存
    if redis_client and bot_guilds:
        try:
            redis_client.setex(
                BOT_GUILDS_CACHE_KEY, 
                BOT_GUILDS_CACHE_TTL, 
                json.dumps(bot_guilds)
            )
            logger.debug(f"ボットのギルドをキャッシュに保存 (TTL: {BOT_GUILDS_CACHE_TTL}秒)")
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    logger.info(f"ボットのギルド取得を完了: {len(bot_guilds)}件 (経過時間: {time.time() - start_time:.2f}秒)")
    return bot_guilds, None, 200

# ギルドをフィルタリング
def filter_guilds(user_guilds: List[Dict], bot_guilds: List[Dict]) -> List[Dict]:
    """
    ユーザーとボットの両方が存在するギルドのみをフィルタリング
    
    Args:
        user_guilds: ユーザーのギルド一覧
        bot_guilds: ボットのギルド一覧
        
    Returns:
        フィルタリングされたギルド一覧
    """
    if not user_guilds or not bot_guilds:
        return []
    
    # ボットが存在するギルドのIDセットを作成
    bot_guild_ids = {guild["id"] for guild in bot_guilds}
    
    # ユーザーとボットの両方が存在するギルドのみをフィルタリング
    filtered_guilds = [
        guild for guild in user_guilds
        if guild["id"] in bot_guild_ids
    ]
    
    return filtered_guilds

# 認証をインポートする代わりに、この関数を直接定義します
# from web.server.middleware.auth import get_discord_token, verify_session

# 認証関連の関数定義
async def verify_session(request: Request) -> Dict[str, Any]:
    """
    セッションの検証とDiscordユーザー情報の取得を行います。
    
    Args:
        request: FastAPIのリクエストオブジェクト
        
    Returns:
        Dict: Discordユーザー情報を含む辞書
        
    Raises:
        HTTPException: 認証に失敗した場合
    """
    session = request.session
    
    if not session or "discord_user" not in session:
        logger.warning("セッションが無効または不足しています")
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    # セッションからユーザー情報を取得
    user_data = session.get("discord_user")
    
    if not user_data or "id" not in user_data:
        logger.warning("セッション内のユーザー情報が無効です")
        raise HTTPException(status_code=401, detail="無効なセッションです")
    
    return user_data

def get_discord_token(request: Request) -> str:
    """
    リクエストセッションからDiscordアクセストークンを取得します。
    
    Args:
        request: FastAPIのリクエストオブジェクト
        
    Returns:
        str: Discordアクセストークン
        
    Raises:
        HTTPException: トークンが見つからない場合
    """
    session = request.session
    
    if not session or "discord_token" not in session:
        logger.warning("セッションにDiscordトークンがありません")
        raise HTTPException(status_code=401, detail="認証が必要です")
    
    token = session.get("discord_token")
    
    if not token:
        logger.warning("Discordトークンが無効です")
        raise HTTPException(status_code=401, detail="無効なトークンです")
    
    return token

# サーバーリストのエンドポイント
@router.get("/guilds")
async def list_guilds(
    request: Request,
    response: Response,
    discord_data: Dict = Depends(verify_session)
) -> Dict[str, Any]:
    """
    ユーザーが管理者で、かつボットが存在するギルド一覧を取得するエンドポイント
    """
    start_time = time.time()
    logger.info("ギルドリスト取得リクエスト受信")
    
    # セッション確認
    if not discord_data:
        logger.warning("無効なセッション")
        raise HTTPException(status_code=401, detail="認証されていません")
    
    user_id = discord_data.get("id")
    access_token = get_discord_token(request)
    
    if not user_id or not access_token:
        logger.warning("ユーザーIDまたはアクセストークンがありません")
        raise HTTPException(status_code=401, detail="有効なトークンがありません")
    
    try:
        # 並列にAPIリクエストを実行
        user_guilds_task = asyncio.create_task(fetch_user_guilds(user_id, access_token))
        bot_guilds_task = asyncio.create_task(fetch_bot_guilds())
        
        # 両方のタスクが完了するまで待機
        user_guilds_result, bot_guilds_result = await asyncio.gather(
            user_guilds_task, 
            bot_guilds_task,
            return_exceptions=True
        )
        
        # 例外のチェック
        if isinstance(user_guilds_result, Exception):
            logger.error(f"ユーザーギルド取得中の例外: {user_guilds_result}")
            user_guilds, error_msg, status = [], str(user_guilds_result), 500
        else:
            user_guilds, error_msg, status = user_guilds_result
        
        if isinstance(bot_guilds_result, Exception):
            logger.error(f"ボットギルド取得中の例外: {bot_guilds_result}")
            bot_guilds, bot_error_msg, bot_status = [], str(bot_guilds_result), 500
        else:
            bot_guilds, bot_error_msg, bot_status = bot_guilds_result
        
        # エラー処理
        if error_msg and not user_guilds:
            # キャッシュから復旧を試みる
            redis_client = get_redis_client()
            if redis_client:
                try:
                    cache_key = USER_GUILDS_CACHE_KEY.format(user_id=user_id)
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.info(f"APIエラーによりキャッシュから復旧: {error_msg}")
                        user_guilds = json.loads(cached_data)
                        response.headers["X-Recovered-From-Cache"] = "true"
                    else:
                        # レート制限の場合はレスポンスヘッダでフロントエンド側に通知
                        if status == 429:
                            response.headers["X-Rate-Limited"] = "true"
                            response.status_code = 429
                            return JSONResponse(
                                status_code=HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "detail": "レート制限に達しました。しばらく待ってから再試行してください。",
                                    "guilds": []
                                }
                            )
                except Exception as e:
                    logger.error(f"キャッシュからの復旧に失敗: {e}")
        
        if bot_error_msg and not bot_guilds:
            # キャッシュから復旧を試みる
            redis_client = get_redis_client()
            if redis_client:
                try:
                    cached_data = redis_client.get(BOT_GUILDS_CACHE_KEY)
                    if cached_data:
                        logger.info(f"APIエラーによりキャッシュから復旧（ボット）: {bot_error_msg}")
                        bot_guilds = json.loads(cached_data)
                        response.headers["X-Recovered-From-Cache"] = "true"
                    else:
                        # レート制限の場合はレスポンスヘッダでフロントエンド側に通知
                        if bot_status == 429:
                            response.headers["X-Rate-Limited"] = "true"
                            response.status_code = 429
                            return JSONResponse(
                                status_code=HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "detail": "レート制限に達しました。しばらく待ってから再試行してください。",
                                    "guilds": []
                                }
                            )
                except Exception as e:
                    logger.error(f"キャッシュからの復旧に失敗（ボット）: {e}")
        
        # ギルドをフィルタリング
        filtered_guilds = filter_guilds(user_guilds, bot_guilds)
        
        logger.info(
            f"ギルドリスト取得完了: ユーザー {len(user_guilds)}件, ボット {len(bot_guilds)}件, "
            f"フィルタリング後 {len(filtered_guilds)}件 (経過時間: {time.time() - start_time:.2f}秒)"
        )
        
        # キャッシュヘッダ
        if "X-Cache" in response.headers and response.headers["X-Cache"] == "HIT":
            logger.debug("キャッシュからデータを返却")
        
        # フロントエンドに公開しない詳細なエラー情報をヘッダに追加
        if error_msg or bot_error_msg:
            response.headers["X-Api-Errors"] = json.dumps({
                "user": error_msg or None,
                "bot": bot_error_msg or None
            })
        
        return {"guilds": filtered_guilds}

    except Exception as e:
        logger.exception(f"ギルドリスト取得中の予期しないエラー: {e}")
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}") 