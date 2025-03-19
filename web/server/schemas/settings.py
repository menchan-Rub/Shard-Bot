from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class SettingsBase(BaseModel):
    """設定の基本モデル"""
    guild_id: str = Field(..., description="Discord サーバーID")

class SettingsCreate(SettingsBase):
    """設定作成モデル"""
    settings: Dict[str, Any] = Field(default={}, description="設定データ")

class SettingsUpdate(BaseModel):
    """設定更新モデル"""
    settings: Dict[str, Any] = Field(default={}, description="更新する設定データ")

class SettingsResponse(SettingsBase):
    """設定レスポンスモデル"""
    id: int
    user_id: int
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# 特定の設定セクション用のモデル
class AutoModSettings(BaseModel):
    """自動モデレーション設定モデル"""
    autoModEnabled: bool = False
    filterBadWords: bool = False
    customBadWords: str = ""
    filterInvites: bool = False
    filterLinks: bool = False
    allowedLinks: str = "youtube.com,twitter.com,discord.com"

class AntiSpamSettings(BaseModel):
    """アンチスパム設定モデル"""
    antiSpamEnabled: bool = False
    duplicateMessageThreshold: int = 3
    duplicateMessageTimeframe: int = 10
    messageSpamThreshold: int = 5
    messageSpamTimeframe: int = 3
    mentionLimit: int = 5
    spamAction: str = "delete"

class RaidProtectionSettings(BaseModel):
    """レイド保護設定モデル"""
    raidProtectionEnabled: bool = False
    raidThreshold: int = 10
    raidTimeframe: int = 60
    raidAction: str = "lockdown"
    accountAgeLimit: int = 7
    requireVerification: bool = False

class CaptchaSettings(BaseModel):
    """キャプチャ設定モデル"""
    captchaEnabled: bool = False
    captchaType: str = "text"
    captchaChannelId: str = ""
    verifiedRoleId: str = ""
    captchaMessage: str = "サーバーへようこそ！認証を完了するために、表示されたキャプチャコードを入力してください。" 