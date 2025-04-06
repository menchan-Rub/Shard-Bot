from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from bot.src.db.database import get_db_session
from bot.src.db.repository import (
    GuildRepository, GuildSettingsRepository, RaidSettingsRepository,
    SpamSettingsRepository, AIModSettingsRepository, AutoResponseSettingsRepository
)
from .auth import get_current_user

# ロガー設定
logger = logging.getLogger('api.settings')

# ルーター設定
router = APIRouter(
    prefix="/settings",
    tags=["設定"],
    responses={401: {"description": "未認証"}}
)

# リクエスト/レスポンスモデル
class GuildSettingsModel(BaseModel):
    prefix: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    log_channel_id: Optional[str] = None
    mod_channel_id: Optional[str] = None
    welcome_channel_id: Optional[str] = None
    goodbye_channel_id: Optional[str] = None
    welcome_message: Optional[str] = None
    goodbye_message: Optional[str] = None

class RaidSettingsModel(BaseModel):
    enabled: Optional[bool] = None
    join_rate_threshold: Optional[int] = None
    join_time_window: Optional[int] = None
    new_account_threshold: Optional[int] = None
    action_type: Optional[str] = None
    lockdown_duration: Optional[int] = None
    notify_channel_id: Optional[str] = None
    notify_role_ids: Optional[str] = None
    excluded_role_ids: Optional[str] = None

class SpamSettingsModel(BaseModel):
    enabled: Optional[bool] = None
    message_rate_limit: Optional[int] = None
    message_time_window: Optional[int] = None
    mention_limit: Optional[int] = None
    role_mention_limit: Optional[int] = None
    duplicate_limit: Optional[int] = None
    url_limit: Optional[int] = None
    allowed_domains: Optional[str] = None
    action_type: Optional[str] = None
    mute_duration: Optional[int] = None
    warning_message: Optional[str] = None
    excluded_role_ids: Optional[str] = None
    excluded_channel_ids: Optional[str] = None

class AIModerationSettingsModel(BaseModel):
    enabled: Optional[bool] = None
    toxicity_threshold: Optional[float] = None
    identity_attack_threshold: Optional[float] = None
    insult_threshold: Optional[float] = None
    threat_threshold: Optional[float] = None
    sexually_explicit_threshold: Optional[float] = None
    custom_words: Optional[str] = None
    action_on_detect: Optional[str] = None
    mute_duration: Optional[int] = None
    notify_mods: Optional[bool] = None
    log_detections: Optional[bool] = None
    exclusion_roles: Optional[str] = None
    exclusion_channels: Optional[str] = None

class AutoResponseSettingsModel(BaseModel):
    enabled: Optional[bool] = None
    response_chance: Optional[float] = None
    cooldown: Optional[int] = None
    ignore_bots: Optional[bool] = None
    ignore_prefixes: Optional[str] = None
    max_context_length: Optional[int] = None
    ai_powered: Optional[bool] = None
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = None
    ai_persona: Optional[str] = None
    custom_responses: Optional[Dict[str, List[str]]] = None

# ヘルパー関数
def check_guild_access(guild_id: str, current_user: dict):
    """ユーザーがギルドにアクセスできるか確認"""
    # 実際のImplementationではDiscord APIを使用して、
    # ユーザーがギルドにアクセスできるか確認する
    # この例では単純化のため常にTrueを返す
    return True

# エンドポイント - 基本設定
@router.get("/guilds/{guild_id}/general")
async def get_guild_settings(
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドの基本設定を取得"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        repo = GuildSettingsRepository(session)
        settings = repo.get_settings(guild_id)
        
        if not settings:
            # 設定がない場合はデフォルト値を返す
            return GuildSettingsModel()
        
        return GuildSettingsModel(
            prefix=settings.prefix,
            language=settings.language,
            timezone=settings.timezone,
            log_channel_id=settings.log_channel_id,
            mod_channel_id=settings.mod_channel_id,
            welcome_channel_id=settings.welcome_channel_id,
            goodbye_channel_id=settings.goodbye_channel_id,
            welcome_message=settings.welcome_message,
            goodbye_message=settings.goodbye_message
        )

@router.patch("/guilds/{guild_id}/general")
async def update_guild_settings(
    settings_update: GuildSettingsModel,
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドの基本設定を更新"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild_repo = GuildRepository(session)
        guild = guild_repo.get_guild_by_id(guild_id)
        
        if not guild:
            # ギルドが存在しない場合は作成
            guild_data = {
                "guild_id": guild_id,
                "name": f"Server {guild_id}",  # 本来はDiscord APIから取得
            }
            guild = guild_repo.create_guild(guild_data)
            if not guild:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ギルド情報の作成に失敗しました"
                )
        
        # 設定を更新
        repo = GuildSettingsRepository(session)
        settings_dict = settings_update.dict(exclude_unset=True)
        success = repo.update_settings(guild_id, settings_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="設定の更新に失敗しました"
            )
        
        return {"message": "設定が更新されました"}

# エンドポイント - レイド対策設定
@router.get("/guilds/{guild_id}/raid")
async def get_raid_settings(
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのレイド対策設定を取得"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        repo = RaidSettingsRepository(session)
        settings = repo.get_settings(guild_id)
        
        if not settings:
            # 設定がない場合はデフォルト値を返す
            return RaidSettingsModel()
        
        return RaidSettingsModel(
            enabled=settings.enabled,
            join_rate_threshold=settings.join_rate_threshold,
            join_time_window=settings.join_time_window,
            new_account_threshold=settings.new_account_threshold,
            action_type=settings.action_type,
            lockdown_duration=settings.lockdown_duration,
            notify_channel_id=settings.notify_channel_id,
            notify_role_ids=settings.notify_role_ids,
            excluded_role_ids=settings.excluded_role_ids
        )

@router.patch("/guilds/{guild_id}/raid")
async def update_raid_settings(
    settings_update: RaidSettingsModel,
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのレイド対策設定を更新"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild_repo = GuildRepository(session)
        guild = guild_repo.get_guild_by_id(guild_id)
        
        if not guild:
            # ギルドが存在しない場合は作成
            guild_data = {
                "guild_id": guild_id,
                "name": f"Server {guild_id}",  # 本来はDiscord APIから取得
            }
            guild = guild_repo.create_guild(guild_data)
            if not guild:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ギルド情報の作成に失敗しました"
                )
        
        # 設定を更新
        repo = RaidSettingsRepository(session)
        settings_dict = settings_update.dict(exclude_unset=True)
        success = repo.update_settings(guild_id, settings_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="設定の更新に失敗しました"
            )
        
        return {"message": "レイド対策設定が更新されました"}

# エンドポイント - スパム対策設定
@router.get("/guilds/{guild_id}/spam")
async def get_spam_settings(
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのスパム対策設定を取得"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        repo = SpamSettingsRepository(session)
        settings = repo.get_settings(guild_id)
        
        if not settings:
            # 設定がない場合はデフォルト値を返す
            return SpamSettingsModel()
        
        return SpamSettingsModel(
            enabled=settings.enabled,
            message_rate_limit=settings.message_rate_limit,
            message_time_window=settings.message_time_window,
            mention_limit=settings.mention_limit,
            role_mention_limit=settings.role_mention_limit,
            duplicate_limit=settings.duplicate_limit,
            url_limit=settings.url_limit,
            allowed_domains=settings.allowed_domains,
            action_type=settings.action_type,
            mute_duration=settings.mute_duration,
            warning_message=settings.warning_message,
            excluded_role_ids=settings.excluded_role_ids,
            excluded_channel_ids=settings.excluded_channel_ids
        )

@router.patch("/guilds/{guild_id}/spam")
async def update_spam_settings(
    settings_update: SpamSettingsModel,
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのスパム対策設定を更新"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild_repo = GuildRepository(session)
        guild = guild_repo.get_guild_by_id(guild_id)
        
        if not guild:
            # ギルドが存在しない場合は作成
            guild_data = {
                "guild_id": guild_id,
                "name": f"Server {guild_id}",  # 本来はDiscord APIから取得
            }
            guild = guild_repo.create_guild(guild_data)
            if not guild:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ギルド情報の作成に失敗しました"
                )
        
        # 設定を更新
        repo = SpamSettingsRepository(session)
        settings_dict = settings_update.dict(exclude_unset=True)
        success = repo.update_settings(guild_id, settings_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="設定の更新に失敗しました"
            )
        
        return {"message": "スパム対策設定が更新されました"}

# エンドポイント - AIモデレーション設定
@router.get("/guilds/{guild_id}/ai-moderation")
async def get_ai_moderation_settings(
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのAIモデレーション設定を取得"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        repo = AIModSettingsRepository(session)
        settings = repo.get_settings(guild_id)
        
        if not settings:
            # 設定がない場合はデフォルト値を返す
            return AIModerationSettingsModel()
        
        return AIModerationSettingsModel(
            enabled=settings.enabled,
            toxicity_threshold=settings.toxicity_threshold,
            identity_attack_threshold=settings.identity_attack_threshold,
            insult_threshold=settings.insult_threshold,
            threat_threshold=settings.threat_threshold,
            sexually_explicit_threshold=settings.sexually_explicit_threshold,
            custom_words=settings.custom_words,
            action_on_detect=settings.action_on_detect,
            mute_duration=settings.mute_duration,
            notify_mods=settings.notify_mods,
            log_detections=settings.log_detections,
            exclusion_roles=settings.exclusion_roles,
            exclusion_channels=settings.exclusion_channels
        )

@router.patch("/guilds/{guild_id}/ai-moderation")
async def update_ai_moderation_settings(
    settings_update: AIModerationSettingsModel,
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドのAIモデレーション設定を更新"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild_repo = GuildRepository(session)
        guild = guild_repo.get_guild_by_id(guild_id)
        
        if not guild:
            # ギルドが存在しない場合は作成
            guild_data = {
                "guild_id": guild_id,
                "name": f"Server {guild_id}",  # 本来はDiscord APIから取得
            }
            guild = guild_repo.create_guild(guild_data)
            if not guild:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ギルド情報の作成に失敗しました"
                )
        
        # 設定を更新
        repo = AIModSettingsRepository(session)
        settings_dict = settings_update.dict(exclude_unset=True)
        success = repo.update_settings(guild_id, settings_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="設定の更新に失敗しました"
            )
        
        return {"message": "AIモデレーション設定が更新されました"}

# エンドポイント - 自動応答設定
@router.get("/guilds/{guild_id}/auto-response")
async def get_auto_response_settings(
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドの自動応答設定を取得"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        repo = AutoResponseSettingsRepository(session)
        settings = repo.get_settings(guild_id)
        
        if not settings:
            # 設定がない場合はデフォルト値を返す
            return AutoResponseSettingsModel()
        
        return AutoResponseSettingsModel(
            enabled=settings.enabled,
            response_chance=settings.response_chance,
            cooldown=settings.cooldown,
            ignore_bots=settings.ignore_bots,
            ignore_prefixes=settings.ignore_prefixes,
            max_context_length=settings.max_context_length,
            ai_powered=settings.ai_powered,
            ai_model=settings.ai_model,
            ai_temperature=settings.ai_temperature,
            ai_persona=settings.ai_persona,
            custom_responses=settings.custom_responses
        )

@router.patch("/guilds/{guild_id}/auto-response")
async def update_auto_response_settings(
    settings_update: AutoResponseSettingsModel,
    guild_id: str = Path(..., description="ギルドID"),
    current_user: dict = Depends(get_current_user)
):
    """ギルドの自動応答設定を更新"""
    if not check_guild_access(guild_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このギルドにアクセスする権限がありません"
        )
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild_repo = GuildRepository(session)
        guild = guild_repo.get_guild_by_id(guild_id)
        
        if not guild:
            # ギルドが存在しない場合は作成
            guild_data = {
                "guild_id": guild_id,
                "name": f"Server {guild_id}",  # 本来はDiscord APIから取得
            }
            guild = guild_repo.create_guild(guild_data)
            if not guild:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ギルド情報の作成に失敗しました"
                )
        
        # 設定を更新
        repo = AutoResponseSettingsRepository(session)
        settings_dict = settings_update.dict(exclude_unset=True)
        success = repo.update_settings(guild_id, settings_dict)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="設定の更新に失敗しました"
            )
        
        return {"message": "自動応答設定が更新されました"} 