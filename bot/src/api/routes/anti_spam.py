from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime
import logging

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, AntiSpamSettings, SpamFilter
from bot.src.api.auth import get_current_user, verify_guild_access
from bot.src.api.models import (
    AntiSpamSettingsResponse, 
    AntiSpamSettingsUpdate,
    SpamFilterResponse,
    SpamFilterCreate,
    SpamFilterUpdate
)

# ルーターの作成
router = APIRouter(
    prefix="/api/anti-spam",
    tags=["anti-spam"],
    responses={404: {"description": "Not found"}},
)

# ロガーの設定
logger = logging.getLogger("api.anti_spam")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# アンチスパム設定の取得
@router.get("/guilds/{guild_id}/settings", response_model=AntiSpamSettingsResponse)
async def get_anti_spam_settings(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのアンチスパム設定を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filters = session.query(SpamFilter).filter(
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).all()
            
            # フィルター情報を構築
            filter_responses = []
            for filter_obj in filters:
                filter_responses.append(SpamFilterResponse(
                    id=filter_obj.id,
                    name=filter_obj.name,
                    enabled=filter_obj.enabled,
                    threshold=filter_obj.threshold,
                    time_window=filter_obj.time_window,
                    action=filter_obj.action,
                    action_duration=filter_obj.action_duration,
                    ignore_roles=filter_obj.ignore_roles,
                    ignore_channels=filter_obj.ignore_channels,
                    created_at=filter_obj.created_at,
                    updated_at=filter_obj.updated_at
                ))
            
            # レスポンスモデルに変換して返す
            return AntiSpamSettingsResponse(
                guild_id=guild_id,
                enabled=spam_settings.enabled,
                log_channel_id=spam_settings.log_channel_id,
                notify_channel_id=spam_settings.notify_channel_id,
                warn_threshold=spam_settings.warn_threshold,
                mute_threshold=spam_settings.mute_threshold,
                kick_threshold=spam_settings.kick_threshold,
                ban_threshold=spam_settings.ban_threshold,
                default_mute_duration=spam_settings.default_mute_duration,
                default_ban_duration=spam_settings.default_ban_duration,
                ignore_roles=spam_settings.ignore_roles,
                ignore_channels=spam_settings.ignore_channels,
                filters=filter_responses,
                created_at=spam_settings.created_at,
                updated_at=spam_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"アンチスパム設定取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# アンチスパム設定の更新
@router.put("/guilds/{guild_id}/settings", response_model=AntiSpamSettingsResponse)
async def update_anti_spam_settings(
    settings: AntiSpamSettingsUpdate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのアンチスパム設定を更新
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # フィルターは除外して設定を更新
            update_data = settings.dict(exclude={"filters"}, exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(spam_settings, field):
                    setattr(spam_settings, field, value)
            
            # 更新日時を設定
            spam_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # スパムフィルターを取得
            filters = session.query(SpamFilter).filter(
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).all()
            
            # フィルター情報を構築
            filter_responses = []
            for filter_obj in filters:
                filter_responses.append(SpamFilterResponse(
                    id=filter_obj.id,
                    name=filter_obj.name,
                    enabled=filter_obj.enabled,
                    threshold=filter_obj.threshold,
                    time_window=filter_obj.time_window,
                    action=filter_obj.action,
                    action_duration=filter_obj.action_duration,
                    ignore_roles=filter_obj.ignore_roles,
                    ignore_channels=filter_obj.ignore_channels,
                    created_at=filter_obj.created_at,
                    updated_at=filter_obj.updated_at
                ))
            
            # 更新された設定を返す
            return AntiSpamSettingsResponse(
                guild_id=guild_id,
                enabled=spam_settings.enabled,
                log_channel_id=spam_settings.log_channel_id,
                notify_channel_id=spam_settings.notify_channel_id,
                warn_threshold=spam_settings.warn_threshold,
                mute_threshold=spam_settings.mute_threshold,
                kick_threshold=spam_settings.kick_threshold,
                ban_threshold=spam_settings.ban_threshold,
                default_mute_duration=spam_settings.default_mute_duration,
                default_ban_duration=spam_settings.default_ban_duration,
                ignore_roles=spam_settings.ignore_roles,
                ignore_channels=spam_settings.ignore_channels,
                filters=filter_responses,
                created_at=spam_settings.created_at,
                updated_at=spam_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"アンチスパム設定更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# アンチスパムの有効/無効切り替え
@router.patch("/guilds/{guild_id}/toggle", response_model=AntiSpamSettingsResponse)
async def toggle_anti_spam(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user),
    enabled: bool = Query(..., description="Enable or disable anti-spam")
):
    """
    指定されたサーバーのアンチスパムの有効/無効を切り替え
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # 有効/無効を切り替え
            spam_settings.enabled = enabled
            
            # 更新日時を設定
            spam_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # スパムフィルターを取得
            filters = session.query(SpamFilter).filter(
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).all()
            
            # フィルター情報を構築
            filter_responses = []
            for filter_obj in filters:
                filter_responses.append(SpamFilterResponse(
                    id=filter_obj.id,
                    name=filter_obj.name,
                    enabled=filter_obj.enabled,
                    threshold=filter_obj.threshold,
                    time_window=filter_obj.time_window,
                    action=filter_obj.action,
                    action_duration=filter_obj.action_duration,
                    ignore_roles=filter_obj.ignore_roles,
                    ignore_channels=filter_obj.ignore_channels,
                    created_at=filter_obj.created_at,
                    updated_at=filter_obj.updated_at
                ))
            
            # 更新された設定を返す
            return AntiSpamSettingsResponse(
                guild_id=guild_id,
                enabled=spam_settings.enabled,
                log_channel_id=spam_settings.log_channel_id,
                notify_channel_id=spam_settings.notify_channel_id,
                warn_threshold=spam_settings.warn_threshold,
                mute_threshold=spam_settings.mute_threshold,
                kick_threshold=spam_settings.kick_threshold,
                ban_threshold=spam_settings.ban_threshold,
                default_mute_duration=spam_settings.default_mute_duration,
                default_ban_duration=spam_settings.default_ban_duration,
                ignore_roles=spam_settings.ignore_roles,
                ignore_channels=spam_settings.ignore_channels,
                filters=filter_responses,
                created_at=spam_settings.created_at,
                updated_at=spam_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"アンチスパム切り替えエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの一覧取得
@router.get("/guilds/{guild_id}/filters", response_model=List[SpamFilterResponse])
async def get_spam_filters(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのスパムフィルター一覧を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filters = session.query(SpamFilter).filter(
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).all()
            
            # フィルター情報を構築
            filter_responses = []
            for filter_obj in filters:
                filter_responses.append(SpamFilterResponse(
                    id=filter_obj.id,
                    name=filter_obj.name,
                    enabled=filter_obj.enabled,
                    threshold=filter_obj.threshold,
                    time_window=filter_obj.time_window,
                    action=filter_obj.action,
                    action_duration=filter_obj.action_duration,
                    ignore_roles=filter_obj.ignore_roles,
                    ignore_channels=filter_obj.ignore_channels,
                    created_at=filter_obj.created_at,
                    updated_at=filter_obj.updated_at
                ))
            
            return filter_responses
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの取得
@router.get("/guilds/{guild_id}/filters/{filter_id}", response_model=SpamFilterResponse)
async def get_spam_filter(
    guild_id: str = Path(..., description="Discord Guild ID"),
    filter_id: str = Path(..., description="Spam Filter ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの特定のスパムフィルターを取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filter_obj = session.query(SpamFilter).filter(
                SpamFilter.id == filter_id,
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).first()
            
            if not filter_obj:
                raise HTTPException(status_code=404, detail="Spam filter not found")
            
            # フィルター情報を返す
            return SpamFilterResponse(
                id=filter_obj.id,
                name=filter_obj.name,
                enabled=filter_obj.enabled,
                threshold=filter_obj.threshold,
                time_window=filter_obj.time_window,
                action=filter_obj.action,
                action_duration=filter_obj.action_duration,
                ignore_roles=filter_obj.ignore_roles,
                ignore_channels=filter_obj.ignore_channels,
                created_at=filter_obj.created_at,
                updated_at=filter_obj.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの作成
@router.post("/guilds/{guild_id}/filters", response_model=SpamFilterResponse)
async def create_spam_filter(
    filter_data: SpamFilterCreate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーに新しいスパムフィルターを作成
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # 新しいスパムフィルターを作成
            new_filter = SpamFilter(
                anti_spam_settings_id=spam_settings.id,
                name=filter_data.name,
                enabled=filter_data.enabled,
                threshold=filter_data.threshold,
                time_window=filter_data.time_window,
                action=filter_data.action,
                action_duration=filter_data.action_duration,
                ignore_roles=filter_data.ignore_roles,
                ignore_channels=filter_data.ignore_channels,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # データベースに追加
            session.add(new_filter)
            session.commit()
            
            # 作成されたフィルターを返す
            return SpamFilterResponse(
                id=new_filter.id,
                name=new_filter.name,
                enabled=new_filter.enabled,
                threshold=new_filter.threshold,
                time_window=new_filter.time_window,
                action=new_filter.action,
                action_duration=new_filter.action_duration,
                ignore_roles=new_filter.ignore_roles,
                ignore_channels=new_filter.ignore_channels,
                created_at=new_filter.created_at,
                updated_at=new_filter.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの更新
@router.put("/guilds/{guild_id}/filters/{filter_id}", response_model=SpamFilterResponse)
async def update_spam_filter(
    filter_data: SpamFilterUpdate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    filter_id: str = Path(..., description="Spam Filter ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのスパムフィルターを更新
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filter_obj = session.query(SpamFilter).filter(
                SpamFilter.id == filter_id,
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).first()
            
            if not filter_obj:
                raise HTTPException(status_code=404, detail="Spam filter not found")
            
            # フィルターを更新
            for field, value in filter_data.dict(exclude_unset=True).items():
                if hasattr(filter_obj, field):
                    setattr(filter_obj, field, value)
            
            # 更新日時を設定
            filter_obj.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新されたフィルターを返す
            return SpamFilterResponse(
                id=filter_obj.id,
                name=filter_obj.name,
                enabled=filter_obj.enabled,
                threshold=filter_obj.threshold,
                time_window=filter_obj.time_window,
                action=filter_obj.action,
                action_duration=filter_obj.action_duration,
                ignore_roles=filter_obj.ignore_roles,
                ignore_channels=filter_obj.ignore_channels,
                created_at=filter_obj.created_at,
                updated_at=filter_obj.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの削除
@router.delete("/guilds/{guild_id}/filters/{filter_id}")
async def delete_spam_filter(
    guild_id: str = Path(..., description="Discord Guild ID"),
    filter_id: str = Path(..., description="Spam Filter ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのスパムフィルターを削除
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filter_obj = session.query(SpamFilter).filter(
                SpamFilter.id == filter_id,
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).first()
            
            if not filter_obj:
                raise HTTPException(status_code=404, detail="Spam filter not found")
            
            # フィルターを削除
            session.delete(filter_obj)
            
            # 変更をコミット
            session.commit()
            
            return {"message": "Spam filter deleted successfully"}
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# スパムフィルターの有効/無効切り替え
@router.patch("/guilds/{guild_id}/filters/{filter_id}/toggle", response_model=SpamFilterResponse)
async def toggle_spam_filter(
    guild_id: str = Path(..., description="Discord Guild ID"),
    filter_id: str = Path(..., description="Spam Filter ID"),
    current_user: dict = Depends(get_current_user),
    enabled: bool = Query(..., description="Enable or disable the spam filter")
):
    """
    指定されたサーバーのスパムフィルターの有効/無効を切り替え
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのアンチスパム設定を取得
            spam_settings = session.query(AntiSpamSettings).filter(
                AntiSpamSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not spam_settings:
                raise HTTPException(status_code=404, detail="Anti-spam settings not found")
            
            # スパムフィルターを取得
            filter_obj = session.query(SpamFilter).filter(
                SpamFilter.id == filter_id,
                SpamFilter.anti_spam_settings_id == spam_settings.id
            ).first()
            
            if not filter_obj:
                raise HTTPException(status_code=404, detail="Spam filter not found")
            
            # 有効/無効を切り替え
            filter_obj.enabled = enabled
            
            # 更新日時を設定
            filter_obj.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新されたフィルターを返す
            return SpamFilterResponse(
                id=filter_obj.id,
                name=filter_obj.name,
                enabled=filter_obj.enabled,
                threshold=filter_obj.threshold,
                time_window=filter_obj.time_window,
                action=filter_obj.action,
                action_duration=filter_obj.action_duration,
                ignore_roles=filter_obj.ignore_roles,
                ignore_channels=filter_obj.ignore_channels,
                created_at=filter_obj.created_at,
                updated_at=filter_obj.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"スパムフィルター切り替えエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 