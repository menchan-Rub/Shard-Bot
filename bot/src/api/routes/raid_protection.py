from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime
import logging

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, RaidProtectionSettings
from bot.src.api.auth import get_current_user, verify_guild_access
from bot.src.api.models import RaidProtectionSettingsResponse, RaidProtectionSettingsUpdate

# ルーターの作成
router = APIRouter(
    prefix="/api/raid-protection",
    tags=["raid-protection"],
    responses={404: {"description": "Not found"}},
)

# ロガーの設定
logger = logging.getLogger("api.raid_protection")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# レイドプロテクション設定の取得
@router.get("/guilds/{guild_id}/settings", response_model=RaidProtectionSettingsResponse)
async def get_raid_protection_settings(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクション設定を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # レスポンスモデルに変換して返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"レイドプロテクション設定取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# レイドプロテクション設定の更新
@router.put("/guilds/{guild_id}/settings", response_model=RaidProtectionSettingsResponse)
async def update_raid_protection_settings(
    settings: RaidProtectionSettingsUpdate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクション設定を更新
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # 設定を更新
            for field, value in settings.dict(exclude_unset=True).items():
                if hasattr(raid_settings, field):
                    setattr(raid_settings, field, value)
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"レイドプロテクション設定更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# レイドプロテクションの有効/無効切り替え
@router.patch("/guilds/{guild_id}/toggle", response_model=RaidProtectionSettingsResponse)
async def toggle_raid_protection(
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user),
    enabled: bool = Path(..., description="Enable or disable raid protection")
):
    """
    指定されたサーバーのレイドプロテクションの有効/無効を切り替え
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # 有効/無効を切り替え
            raid_settings.enabled = enabled
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"レイドプロテクション切り替えエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ホワイトリストにロールを追加
@router.post("/guilds/{guild_id}/whitelist/roles/{role_id}", response_model=RaidProtectionSettingsResponse)
async def add_whitelisted_role(
    guild_id: str = Path(..., description="Discord Guild ID"),
    role_id: str = Path(..., description="Discord Role ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクションホワイトリストにロールを追加
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # ホワイトリストにロールを追加
            if not raid_settings.whitelisted_roles:
                raid_settings.whitelisted_roles = [role_id]
            elif role_id not in raid_settings.whitelisted_roles:
                raid_settings.whitelisted_roles.append(role_id)
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"ホワイトリストロール追加エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ホワイトリストからロールを削除
@router.delete("/guilds/{guild_id}/whitelist/roles/{role_id}", response_model=RaidProtectionSettingsResponse)
async def remove_whitelisted_role(
    guild_id: str = Path(..., description="Discord Guild ID"),
    role_id: str = Path(..., description="Discord Role ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクションホワイトリストからロールを削除
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # ホワイトリストからロールを削除
            if raid_settings.whitelisted_roles and role_id in raid_settings.whitelisted_roles:
                raid_settings.whitelisted_roles.remove(role_id)
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"ホワイトリストロール削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ホワイトリストにユーザーを追加
@router.post("/guilds/{guild_id}/whitelist/users/{user_id}", response_model=RaidProtectionSettingsResponse)
async def add_whitelisted_user(
    guild_id: str = Path(..., description="Discord Guild ID"),
    user_id: str = Path(..., description="Discord User ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクションホワイトリストにユーザーを追加
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # ホワイトリストにユーザーを追加
            if not raid_settings.whitelisted_users:
                raid_settings.whitelisted_users = [user_id]
            elif user_id not in raid_settings.whitelisted_users:
                raid_settings.whitelisted_users.append(user_id)
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"ホワイトリストユーザー追加エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ホワイトリストからユーザーを削除
@router.delete("/guilds/{guild_id}/whitelist/users/{user_id}", response_model=RaidProtectionSettingsResponse)
async def remove_whitelisted_user(
    guild_id: str = Path(..., description="Discord Guild ID"),
    user_id: str = Path(..., description="Discord User ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーのレイドプロテクションホワイトリストからユーザーを削除
    """
    # ギルドへのアクセス権を確認（管理者権限が必要）
    await verify_guild_access(current_user, guild_id, admin_required=True)
    
    try:
        with get_db_session() as session:
            # サーバーのレイドプロテクション設定を取得
            raid_settings = session.query(RaidProtectionSettings).filter(
                RaidProtectionSettings.guild.has(discord_id=guild_id)
            ).first()
            
            if not raid_settings:
                raise HTTPException(status_code=404, detail="Raid protection settings not found")
            
            # ホワイトリストからユーザーを削除
            if raid_settings.whitelisted_users and user_id in raid_settings.whitelisted_users:
                raid_settings.whitelisted_users.remove(user_id)
            
            # 更新日時を設定
            raid_settings.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された設定を返す
            return RaidProtectionSettingsResponse(
                guild_id=guild_id,
                enabled=raid_settings.enabled,
                join_rate_threshold=raid_settings.join_rate_threshold,
                join_rate_time_window=raid_settings.join_rate_time_window,
                new_account_threshold=raid_settings.new_account_threshold,
                verification_level_action=raid_settings.verification_level_action,
                lockdown_duration=raid_settings.lockdown_duration,
                action_type=raid_settings.action_type,
                notify_channel_id=raid_settings.notify_channel_id,
                log_channel_id=raid_settings.log_channel_id,
                auto_action=raid_settings.auto_action,
                whitelisted_roles=raid_settings.whitelisted_roles,
                whitelisted_users=raid_settings.whitelisted_users,
                created_at=raid_settings.created_at,
                updated_at=raid_settings.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"ホワイトリストユーザー削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 