"""
APIで使用されるPydanticモデル定義
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# 認証関連モデル
class TokenRequest(BaseModel):
    """トークン要求モデル"""
    code: str = Field(..., description="Discord OAuth2認証コード")
    redirect_uri: Optional[str] = Field(None, description="リダイレクトURI")

class TokenResponse(BaseModel):
    """トークンレスポンスモデル"""
    access_token: str = Field(..., description="アクセストークン")
    token_type: str = Field("bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")
    refresh_token: Optional[str] = Field(None, description="リフレッシュトークン")

class UserResponse(BaseModel):
    """ユーザー情報レスポンスモデル"""
    id: str = Field(..., description="Discord ユーザーID")
    username: str = Field(..., description="ユーザー名")
    discriminator: str = Field(..., description="ディスクリミネーター")
    avatar: Optional[str] = Field(None, description="アバターURL")
    email: Optional[str] = Field(None, description="メールアドレス")
    verified: Optional[bool] = Field(None, description="認証済みかどうか")
    locale: Optional[str] = Field(None, description="ロケール")
    created_at: Optional[datetime] = Field(None, description="作成日時")

# サーバー関連モデル
class GuildResponse(BaseModel):
    """サーバー情報レスポンスモデル"""
    id: str = Field(..., description="Discord サーバーID")
    name: str = Field(..., description="サーバー名")
    icon: Optional[str] = Field(None, description="アイコンURL")
    owner: bool = Field(False, description="オーナーかどうか")
    permissions: str = Field("0", description="権限値")
    features: List[str] = Field(default_factory=list, description="サーバーの機能")
    joined_at: Optional[datetime] = Field(None, description="参加日時")
    member_count: Optional[int] = Field(None, description="メンバー数")
    description: Optional[str] = Field(None, description="説明")

# モデレーション関連モデル
class InfractionResponse(BaseModel):
    """違反レスポンスモデル"""
    id: int = Field(..., description="違反ID")
    guild_id: str = Field(..., description="サーバーID")
    user_id: str = Field(..., description="ユーザーID")
    moderator_id: str = Field(..., description="モデレーターID")
    action_type: str = Field(..., description="アクションタイプ")
    reason: Optional[str] = Field(None, description="理由")
    duration: Optional[int] = Field(None, description="期間（分）")
    active: bool = Field(..., description="アクティブかどうか")
    created_at: datetime = Field(..., description="作成日時")
    expires_at: Optional[datetime] = Field(None, description="有効期限")

class InfractionCreate(BaseModel):
    """違反作成モデル"""
    user_id: str = Field(..., description="ユーザーID")
    action_type: str = Field(..., description="アクションタイプ")
    reason: Optional[str] = Field(None, description="理由")
    duration: Optional[int] = Field(None, description="期間（分）")
    
    @validator('action_type')
    def validate_action_type(cls, v):
        allowed_types = ['warn', 'mute', 'kick', 'ban']
        if v not in allowed_types:
            raise ValueError(f"action_type must be one of {allowed_types}")
        return v

# モデレーション設定
class ModerationSettingsResponse(BaseModel):
    """モデレーション設定レスポンスモデル"""
    guild_id: str = Field(..., description="サーバーID")
    warning_threshold: int = Field(..., description="警告の閾値")
    mute_threshold: int = Field(..., description="ミュートの閾値")
    kick_threshold: int = Field(..., description="キックの閾値")
    ban_threshold: int = Field(..., description="バンの閾値")
    default_mute_duration: int = Field(..., description="デフォルトのミュート期間（分）")
    warn_message: Optional[str] = Field(None, description="警告メッセージ")
    log_moderation_actions: bool = Field(..., description="モデレーションアクションをログに記録するかどうか")
    log_channel_id: Optional[str] = Field(None, description="ログチャンネルID")
    badwords_filter_enabled: bool = Field(..., description="悪い言葉フィルターを有効にするかどうか")
    badwords_list: List[str] = Field(default_factory=list, description="悪い言葉リスト")
    badwords_action: str = Field(..., description="悪い言葉に対するアクション")
    badwords_action_duration: Optional[int] = Field(None, description="悪い言葉に対するアクションの期間（分）")
    warn_dm_enabled: bool = Field(..., description="DMでの警告を有効にするかどうか")
    auto_moderation_enabled: bool = Field(..., description="自動モデレーションを有効にするかどうか")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

class ModerationSettingsUpdate(BaseModel):
    """モデレーション設定更新モデル"""
    warning_threshold: Optional[int] = Field(None, description="警告の閾値")
    mute_threshold: Optional[int] = Field(None, description="ミュートの閾値")
    kick_threshold: Optional[int] = Field(None, description="キックの閾値")
    ban_threshold: Optional[int] = Field(None, description="バンの閾値")
    default_mute_duration: Optional[int] = Field(None, description="デフォルトのミュート期間（分）")
    warn_message: Optional[str] = Field(None, description="警告メッセージ")
    log_moderation_actions: Optional[bool] = Field(None, description="モデレーションアクションをログに記録するかどうか")
    log_channel_id: Optional[str] = Field(None, description="ログチャンネルID")
    badwords_filter_enabled: Optional[bool] = Field(None, description="悪い言葉フィルターを有効にするかどうか")
    badwords_list: Optional[List[str]] = Field(None, description="悪い言葉リスト")
    badwords_action: Optional[str] = Field(None, description="悪い言葉に対するアクション")
    badwords_action_duration: Optional[int] = Field(None, description="悪い言葉に対するアクションの期間（分）")
    warn_dm_enabled: Optional[bool] = Field(None, description="DMでの警告を有効にするかどうか")
    auto_moderation_enabled: Optional[bool] = Field(None, description="自動モデレーションを有効にするかどうか")
    
    @validator('badwords_action')
    def validate_badwords_action(cls, v):
        if v is not None:
            allowed_actions = ['none', 'delete', 'warn', 'mute', 'kick', 'ban']
            if v not in allowed_actions:
                raise ValueError(f"badwords_action must be one of {allowed_actions}")
        return v

# レイド対策関連モデル
class RaidProtectionSettingsResponse(BaseModel):
    """レイド対策設定レスポンスモデル"""
    guild_id: str = Field(..., description="サーバーID")
    enabled: bool = Field(..., description="有効かどうか")
    action: str = Field(..., description="レイド検出時のアクション")
    join_rate_threshold: int = Field(..., description="参加速度の閾値（ユーザー数）")
    join_rate_time_window: int = Field(..., description="参加速度の時間枠（秒）")
    new_account_threshold: int = Field(..., description="新規アカウント判定の閾値（日数）")
    verification_level: int = Field(..., description="検証レベル")
    lockdown_duration: int = Field(..., description="ロックダウン期間（分）")
    lockdown_channels: List[str] = Field(default_factory=list, description="ロックダウン対象チャンネルID")
    notification_channel_id: Optional[str] = Field(None, description="通知チャンネルID")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

class RaidProtectionSettingsUpdate(BaseModel):
    """レイド対策設定更新モデル"""
    enabled: Optional[bool] = Field(None, description="有効かどうか")
    action: Optional[str] = Field(None, description="レイド検出時のアクション")
    join_rate_threshold: Optional[int] = Field(None, description="参加速度の閾値（ユーザー数）")
    join_rate_time_window: Optional[int] = Field(None, description="参加速度の時間枠（秒）")
    new_account_threshold: Optional[int] = Field(None, description="新規アカウント判定の閾値（日数）")
    verification_level: Optional[int] = Field(None, description="検証レベル")
    lockdown_duration: Optional[int] = Field(None, description="ロックダウン期間（分）")
    lockdown_channels: Optional[List[str]] = Field(None, description="ロックダウン対象チャンネルID")
    notification_channel_id: Optional[str] = Field(None, description="通知チャンネルID")
    
    @validator('action')
    def validate_action(cls, v):
        if v is not None:
            allowed_actions = ['none', 'alert', 'lockdown', 'verification']
            if v not in allowed_actions:
                raise ValueError(f"action must be one of {allowed_actions}")
        return v

# アンチスパム関連モデル
class AntiSpamSettingsResponse(BaseModel):
    """アンチスパム設定レスポンスモデル"""
    guild_id: str = Field(..., description="サーバーID")
    enabled: bool = Field(..., description="有効かどうか")
    message_threshold: int = Field(..., description="メッセージの閾値")
    message_time_window: int = Field(..., description="メッセージの時間枠（秒）")
    mention_threshold: int = Field(..., description="メンションの閾値")
    duplicate_threshold: int = Field(..., description="重複メッセージの閾値")
    emoji_threshold: int = Field(..., description="絵文字の閾値")
    action: str = Field(..., description="スパム検出時のアクション")
    action_duration: int = Field(..., description="アクションの期間（分）")
    ignored_channels: List[str] = Field(default_factory=list, description="無視するチャンネルID")
    ignored_roles: List[str] = Field(default_factory=list, description="無視するロールID")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

class AntiSpamSettingsUpdate(BaseModel):
    """アンチスパム設定更新モデル"""
    enabled: Optional[bool] = Field(None, description="有効かどうか")
    message_threshold: Optional[int] = Field(None, description="メッセージの閾値")
    message_time_window: Optional[int] = Field(None, description="メッセージの時間枠（秒）")
    mention_threshold: Optional[int] = Field(None, description="メンションの閾値")
    duplicate_threshold: Optional[int] = Field(None, description="重複メッセージの閾値")
    emoji_threshold: Optional[int] = Field(None, description="絵文字の閾値")
    action: Optional[str] = Field(None, description="スパム検出時のアクション")
    action_duration: Optional[int] = Field(None, description="アクションの期間（分）")
    ignored_channels: Optional[List[str]] = Field(None, description="無視するチャンネルID")
    ignored_roles: Optional[List[str]] = Field(None, description="無視するロールID")

# 自動応答関連モデル
class AutoResponsePatternResponse(BaseModel):
    """自動応答パターンレスポンスモデル"""
    id: int = Field(..., description="パターンID")
    guild_id: str = Field(..., description="サーバーID")
    trigger: str = Field(..., description="トリガー")
    response: str = Field(..., description="応答")
    trigger_type: str = Field(..., description="トリガータイプ")
    chance: float = Field(..., description="応答確率")
    enabled: bool = Field(..., description="有効かどうか")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

class AutoResponsePatternCreate(BaseModel):
    """自動応答パターン作成モデル"""
    trigger: str = Field(..., description="トリガー")
    response: str = Field(..., description="応答")
    trigger_type: str = Field("exact", description="トリガータイプ")
    chance: float = Field(100.0, ge=0.0, le=100.0, description="応答確率")
    enabled: bool = Field(True, description="有効かどうか")
    
    @validator('trigger_type')
    def validate_trigger_type(cls, v):
        allowed_types = ['exact', 'contains', 'starts_with', 'ends_with', 'regex']
        if v not in allowed_types:
            raise ValueError(f"trigger_type must be one of {allowed_types}")
        return v

class AutoResponseSettingsResponse(BaseModel):
    """自動応答設定レスポンスモデル"""
    guild_id: str = Field(..., description="サーバーID")
    enabled: bool = Field(..., description="有効かどうか")
    cooldown: int = Field(..., description="クールダウン（秒）")
    ignore_bots: bool = Field(..., description="ボットを無視するかどうか")
    ignore_webhooks: bool = Field(..., description="Webhookを無視するかどうか")
    ignore_prefixes: List[str] = Field(default_factory=list, description="無視するプレフィックス")
    ai_enabled: bool = Field(..., description="AI応答を有効にするかどうか")
    ai_persona: Optional[str] = Field(None, description="AIのペルソナ設定")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

class AutoResponseSettingsUpdate(BaseModel):
    """自動応答設定更新モデル"""
    enabled: Optional[bool] = Field(None, description="有効かどうか")
    cooldown: Optional[int] = Field(None, description="クールダウン（秒）")
    ignore_bots: Optional[bool] = Field(None, description="ボットを無視するかどうか")
    ignore_webhooks: Optional[bool] = Field(None, description="Webhookを無視するかどうか")
    ignore_prefixes: Optional[List[str]] = Field(None, description="無視するプレフィックス")
    ai_enabled: Optional[bool] = Field(None, description="AI応答を有効にするかどうか")
    ai_persona: Optional[str] = Field(None, description="AIのペルソナ設定") 