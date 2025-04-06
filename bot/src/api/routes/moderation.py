from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, ModerationSettings, UserInfraction, ModerationAction
from bot.src.modules.moderation.infractions import InfractionManager
from bot.src.api.auth import get_current_user, verify_guild_access
from bot.src.api.models import (
    InfractionResponse, 
    InfractionCreate, 
    ModerationSettingsResponse, 
    ModerationSettingsUpdate
)

# ルーターの作成
router = APIRouter(
    prefix="/api/moderation",
    tags=["moderation"],
    responses={404: {"description": "Not found"}},
)

# ロガーの設定
logger = logging.getLogger("api.moderation")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# モデレーション設定の取得
@router.get("/guilds/{guild_id}/settings", response_model=ModerationSettingsResponse)
async def get_moderation_settings(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのモデレーション設定を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのモデレーション設定を取得
            moderation_settings = session.query(ModerationSettings).filter(
                ModerationSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not moderation_settings:
                raise HTTPException(status_code=404, detail="Moderation settings not found")
            
            # レスポンスモデルに変換して返す
            return ModerationSettingsResponse(
                guild_id=guild_id,
                warning_threshold=moderation_settings.warning_threshold,
                mute_threshold=moderation_settings.mute_threshold,
                kick_threshold=moderation_settings.kick_threshold,
                ban_threshold=moderation_settings.ban_threshold,
                default_mute_duration=moderation_settings.default_mute_duration,
                warn_message=moderation_settings.warn_message,
                log_moderation_actions=moderation_settings.log_moderation_actions,
                log_channel_id=moderation_settings.log_channel_id,
                badwords_filter_enabled=moderation_settings.badwords_filter_enabled,
                badwords_list=moderation_settings.badwords_list,
                badwords_action=moderation_settings.badwords_action,
                badwords_action_duration=moderation_settings.badwords_action_duration,
                warn_dm_enabled=moderation_settings.warn_dm_enabled,
                auto_moderation_enabled=moderation_settings.auto_moderation_enabled,
                created_at=moderation_settings.created_at,
                updated_at=moderation_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"モデレーション設定取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# モデレーション設定の更新
@router.put("/guilds/{guild_id}/settings", response_model=ModerationSettingsResponse)
async def update_moderation_settings(
    settings: ModerationSettingsUpdate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのモデレーション設定を更新
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのモデレーション設定を取得
            moderation_settings = session.query(ModerationSettings).filter(
                ModerationSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not moderation_settings:
                raise HTTPException(status_code=404, detail="Moderation settings not found")
            
            # 設定を更新
            for field, value in settings.dict(exclude_unset=True).items():
                if hasattr(moderation_settings, field):
                    setattr(moderation_settings, field, value)
            
            # 更新日時を設定
            moderation_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return ModerationSettingsResponse(
                guild_id=guild_id,
                warning_threshold=moderation_settings.warning_threshold,
                mute_threshold=moderation_settings.mute_threshold,
                kick_threshold=moderation_settings.kick_threshold,
                ban_threshold=moderation_settings.ban_threshold,
                default_mute_duration=moderation_settings.default_mute_duration,
                warn_message=moderation_settings.warn_message,
                log_moderation_actions=moderation_settings.log_moderation_actions,
                log_channel_id=moderation_settings.log_channel_id,
                badwords_filter_enabled=moderation_settings.badwords_filter_enabled,
                badwords_list=moderation_settings.badwords_list,
                badwords_action=moderation_settings.badwords_action,
                badwords_action_duration=moderation_settings.badwords_action_duration,
                warn_dm_enabled=moderation_settings.warn_dm_enabled,
                auto_moderation_enabled=moderation_settings.auto_moderation_enabled,
                created_at=moderation_settings.created_at,
                updated_at=moderation_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"モデレーション設定更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ユーザーの違反履歴の取得
@router.get("/guilds/{guild_id}/users/{user_id}/infractions", response_model=List[InfractionResponse])
async def get_user_infractions(
    guild_id: str = Path(..., description="Discord Guild ID"),
    user_id: str = Path(..., description="Discord User ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーとユーザーの違反履歴を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # ユーザーの違反履歴を取得
            infractions = session.query(UserInfraction).filter(
                UserInfraction.guild.has(discord_id=guild_id),
                UserInfraction.user_id == user_id
            ).order_by(
                UserInfraction.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            # レスポンスリストを構築
            result = []
            for infraction in infractions:
                result.append(InfractionResponse(
                    id=infraction.id,
                    guild_id=guild_id,
                    user_id=infraction.user_id,
                    moderator_id=infraction.moderator_id,
                    action_type=infraction.action_type,
                    reason=infraction.reason,
                    duration=infraction.duration,
                    active=infraction.active,
                    created_at=infraction.created_at,
                    expires_at=infraction.expires_at
                ))
            
            return result
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"違反履歴取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 違反の作成
@router.post("/guilds/{guild_id}/infractions", response_model=InfractionResponse)
async def create_infraction(
    infraction: InfractionCreate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    新しい違反を作成
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        # InfractionManagerを使用して違反を作成
        infraction_manager = InfractionManager(None)  # Botインスタンスの代わりにNoneを渡す（API経由の場合）
        
        # 違反タイプに応じて処理を分岐
        infraction_id = None
        if infraction.action_type == "warn":
            infraction_id = await infraction_manager.warn_user(
                guild_id=guild_id,
                moderator_id=current_user["id"],
                user_id=infraction.user_id,
                reason=infraction.reason
            )
        elif infraction.action_type == "mute":
            infraction_id = await infraction_manager.mute_user(
                guild_id=guild_id,
                moderator_id=current_user["id"],
                user_id=infraction.user_id,
                reason=infraction.reason,
                duration=infraction.duration or 60  # デフォルトは60分
            )
        elif infraction.action_type == "kick":
            infraction_id = await infraction_manager.kick_user(
                guild_id=guild_id,
                moderator_id=current_user["id"],
                user_id=infraction.user_id,
                reason=infraction.reason
            )
        elif infraction.action_type == "ban":
            infraction_id = await infraction_manager.ban_user(
                guild_id=guild_id,
                moderator_id=current_user["id"],
                user_id=infraction.user_id,
                reason=infraction.reason,
                delete_message_days=1
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action type: {infraction.action_type}")
        
        # 作成された違反を取得
        with get_db_session() as session:
            created_infraction = session.query(UserInfraction).filter(
                UserInfraction.id == infraction_id
            ).first()
            
            if not created_infraction:
                raise HTTPException(status_code=404, detail="Created infraction not found")
            
            # レスポンスを返す
            return InfractionResponse(
                id=created_infraction.id,
                guild_id=guild_id,
                user_id=created_infraction.user_id,
                moderator_id=created_infraction.moderator_id,
                action_type=created_infraction.action_type,
                reason=created_infraction.reason,
                duration=created_infraction.duration,
                active=created_infraction.active,
                created_at=created_infraction.created_at,
                expires_at=created_infraction.expires_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"違反作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 違反の無効化
@router.delete("/guilds/{guild_id}/infractions/{infraction_id}", response_model=InfractionResponse)
async def delete_infraction(
    guild_id: str = Path(..., description="Discord Guild ID"),
    infraction_id: str = Path(..., description="Infraction ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    違反を無効化（実際には削除せず、activeフラグをFalseに設定）
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # 違反を取得
            infraction = session.query(UserInfraction).filter(
                UserInfraction.id == infraction_id,
                UserInfraction.guild.has(discord_id=guild_id)
            ).first()
            
            if not infraction:
                raise HTTPException(status_code=404, detail="Infraction not found")
            
            # 権限チェック（サーバー管理者またはその違反を作成したモデレーターのみ無効化可能）
            if not current_user.get("is_admin") and infraction.moderator_id != current_user["id"]:
                raise HTTPException(status_code=403, detail="You can only delete infractions you created unless you are a server admin")
            
            # 無効化
            infraction.active = False
            
            # モデレーションアクションを記録
            action = ModerationAction(
                guild_id=infraction.guild_id,
                user_id=infraction.user_id,
                moderator_id=current_user["id"],
                action_type="infraction_deleted",
                details=f"Deleted infraction {infraction_id} (originally {infraction.action_type})"
            )
            session.add(action)
            
            # 変更をコミット
            session.commit()
            
            # 更新された違反を返す
            return InfractionResponse(
                id=infraction.id,
                guild_id=guild_id,
                user_id=infraction.user_id,
                moderator_id=infraction.moderator_id,
                action_type=infraction.action_type,
                reason=infraction.reason,
                duration=infraction.duration,
                active=infraction.active,
                created_at=infraction.created_at,
                expires_at=infraction.expires_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"違反無効化エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# モデレーションアクションログの取得
@router.get("/guilds/{guild_id}/actions", response_model=List[dict])
async def get_moderation_actions(
    guild_id: str = Path(..., description="Discord Guild ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのモデレーションアクションログを取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # モデレーションアクションを取得
            actions = session.query(ModerationAction).filter(
                ModerationAction.guild.has(discord_id=guild_id)
            ).order_by(
                ModerationAction.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            # レスポンスリストを構築
            result = []
            for action in actions:
                result.append({
                    "id": action.id,
                    "guild_id": guild_id,
                    "user_id": action.user_id,
                    "moderator_id": action.moderator_id,
                    "action_type": action.action_type,
                    "details": action.details,
                    "created_at": action.created_at
                })
            
            return result
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"モデレーションアクション取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 禁止ワードリストの取得
@router.get("/guilds/{guild_id}/badwords", response_model=List[str])
async def get_badwords(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの禁止ワードリストを取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのモデレーション設定を取得
            moderation_settings = session.query(ModerationSettings).filter(
                ModerationSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not moderation_settings:
                raise HTTPException(status_code=404, detail="Moderation settings not found")
            
            # 禁止ワードリストを返す
            return moderation_settings.badwords_list
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"禁止ワードリスト取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 禁止ワードの追加
@router.post("/guilds/{guild_id}/badwords", response_model=List[str])
async def add_badword(
    word: str,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの禁止ワードリストに単語を追加
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのモデレーション設定を取得
            moderation_settings = session.query(ModerationSettings).filter(
                ModerationSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not moderation_settings:
                raise HTTPException(status_code=404, detail="Moderation settings not found")
            
            # 禁止ワードリストに追加
            if not moderation_settings.badwords_list:
                moderation_settings.badwords_list = [word]
            elif word not in moderation_settings.badwords_list:
                moderation_settings.badwords_list.append(word)
            
            # 変更をコミット
            session.commit()
            
            # 更新された禁止ワードリストを返す
            return moderation_settings.badwords_list
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"禁止ワード追加エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 禁止ワードの削除
@router.delete("/guilds/{guild_id}/badwords/{word}", response_model=List[str])
async def remove_badword(
    guild_id: str = Path(..., description="Discord Guild ID"),
    word: str = Path(..., description="Word to remove"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの禁止ワードリストから単語を削除
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのモデレーション設定を取得
            moderation_settings = session.query(ModerationSettings).filter(
                ModerationSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not moderation_settings:
                raise HTTPException(status_code=404, detail="Moderation settings not found")
            
            # 禁止ワードリストから削除
            if moderation_settings.badwords_list and word in moderation_settings.badwords_list:
                moderation_settings.badwords_list.remove(word)
            
            # 変更をコミット
            session.commit()
            
            # 更新された禁止ワードリストを返す
            return moderation_settings.badwords_list
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"禁止ワード削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 