from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from database.database import get_db
from routes.auth import get_current_user
from models.settings import BotSettings
from schemas.settings import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
async def get_settings(
    guild_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ボットの設定を取得する"""
    try:
        # ユーザーが管理するサーバーの設定を取得
        if guild_id:
            # 特定のサーバーの設定を取得
            settings = db.query(BotSettings).filter(
                BotSettings.guild_id == guild_id,
                BotSettings.user_id == current_user.id
            ).first()
            
            if not settings:
                # 設定が存在しない場合はデフォルト値を返す
                return {
                    "prefix": "!",
                    "language": "ja",
                    "timezone": "Asia/Tokyo",
                    "welcomeEnabled": False,
                    "welcomeMessage": "ようこそ {user} さん！{server}へお越しいただきありがとうございます。",
                    "leaveEnabled": False,
                    "leaveMessage": "{user} さんがサーバーを退出しました。",
                    "welcomeChannelId": "",
                    "loggingEnabled": False,
                    "logChannelId": "",
                    "logMessageDelete": True,
                    "logMessageEdit": True,
                    "logMemberJoin": True,
                    "logMemberLeave": True,
                    "logMemberBan": True,
                    "logChannelChanges": True,
                    "logRoleChanges": True,
                    "logVoiceChanges": True,
                    "levelsEnabled": True,
                    "automodEnabled": False,
                    "raidProtectionEnabled": False,
                    "musicEnabled": False,
                    "autoResponseEnabled": False,
                    # 自動モデレーション設定
                    "autoModEnabled": False,
                    "filterBadWords": False,
                    "customBadWords": "",
                    "filterInvites": False,
                    "filterLinks": False,
                    "allowedLinks": "youtube.com,twitter.com,discord.com",
                    # アンチスパム設定
                    "antiSpamEnabled": False,
                    "duplicateMessageThreshold": 3,
                    "duplicateMessageTimeframe": 10,
                    "messageSpamThreshold": 5,
                    "messageSpamTimeframe": 3,
                    "mentionLimit": 5,
                    "spamAction": "delete",
                    # レイド保護設定
                    "raidThreshold": 10,
                    "raidTimeframe": 60,
                    "raidAction": "lockdown",
                    "accountAgeLimit": 7,
                    "requireVerification": False,
                    # キャプチャ設定
                    "captchaEnabled": False,
                    "captchaType": "text",
                    "captchaChannelId": "",
                    "verifiedRoleId": "",
                    "captchaMessage": "サーバーへようこそ！認証を完了するために、表示されたキャプチャコードを入力してください。"
                }
            
            return settings.settings
        else:
            # サーバーIDが指定されていない場合はエラー
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="サーバーIDが指定されていません"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"設定の取得に失敗しました: {str(e)}"
        )

@router.post("/{section}")
async def update_settings(
    section: str,
    update_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ボットの設定を更新する"""
    try:
        guild_id = update_data.get("guildId")
        settings_data = update_data.get("settings", {})
        
        if not guild_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="サーバーIDが指定されていません"
            )
            
        # 設定を取得または作成
        settings = db.query(BotSettings).filter(
            BotSettings.guild_id == guild_id,
            BotSettings.user_id == current_user.id
        ).first()
        
        if not settings:
            # 新しい設定レコードを作成
            settings = BotSettings(
                guild_id=guild_id,
                user_id=current_user.id,
                settings=settings_data
            )
            db.add(settings)
        else:
            # 既存の設定を更新
            current_settings = settings.settings
            current_settings.update(settings_data)
            settings.settings = current_settings
            
        db.commit()
        db.refresh(settings)
        
        return {
            "status": "success",
            "message": f"{section}の設定を更新しました",
            "data": {
                "settings": settings.settings
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"設定の更新に失敗しました: {str(e)}"
        )

@router.post("/automod")
async def update_automod_settings(
    update_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """自動モデレーション設定を更新する"""
    return await update_settings("automod", update_data, current_user, db)

@router.post("/antispam")
async def update_antispam_settings(
    update_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """アンチスパム設定を更新する"""
    return await update_settings("antispam", update_data, current_user, db)

@router.post("/raidprotection")
async def update_raid_protection_settings(
    update_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """レイド保護設定を更新する"""
    return await update_settings("raidprotection", update_data, current_user, db)

@router.post("/captcha")
async def update_captcha_settings(
    update_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """キャプチャ設定を更新する"""
    return await update_settings("captcha", update_data, current_user, db) 