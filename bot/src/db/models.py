from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    ForeignKey, Table, DateTime, JSON, Enum, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

Base = declarative_base()

# 多対多の関連付けのためのヘルパーテーブル
guild_users = Table(
    'guild_users',
    Base.metadata,
    Column('guild_id', Integer, ForeignKey('guilds.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

# 権限レベルの列挙型
class PermissionLevel(enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

class User(Base):
    """ユーザー情報を保持するテーブル"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), nullable=False, unique=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    guilds = relationship("Guild", secondary=guild_users, back_populates="users")
    logs = relationship("AuditLog", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")

class UserSession(Base):
    """ユーザーセッションモデル"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    
    # リレーションシップ
    user = relationship('User', back_populates='sessions')
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, expires_at='{self.expires_at}')>"

class Guild(Base):
    """サーバー(ギルド)情報"""
    __tablename__ = 'guilds'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(255))
    member_count = Column(Integer, default=0)
    owner_id = Column(String(20), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    premium_tier = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    users = relationship("User", secondary=guild_users, back_populates="guilds")
    settings = relationship("GuildSettings", uselist=False, back_populates="guild")
    ai_mod_settings = relationship("AIModSettings", uselist=False, back_populates="guild")
    moderation_settings = relationship("ModerationSettings", uselist=False, back_populates="guild")
    auto_response_settings = relationship("AutoResponseSettings", uselist=False, back_populates="guild")
    raid_settings = relationship("RaidSettings", uselist=False, back_populates="guild")
    spam_settings = relationship("SpamSettings", uselist=False, back_populates="guild")
    logs = relationship("AuditLog", back_populates="guild")
    commands = relationship("CustomCommand", back_populates="guild")

class GuildSettings(Base):
    __tablename__ = 'guild_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    prefix = Column(String, default='!')
    language = Column(String, default='ja')
    timezone = Column(String, default='Asia/Tokyo')
    
    # 機能フラグ
    ai_moderation_enabled = Column(Boolean, default=False)
    auto_response_enabled = Column(Boolean, default=False)
    raid_protection_enabled = Column(Boolean, default=True)
    spam_protection_enabled = Column(Boolean, default=True)
    voice_enabled = Column(Boolean, default=False)
    event_system_enabled = Column(Boolean, default=False)
    
    # ウェルカムメッセージ設定
    welcome_channel_id = Column(String)
    welcome_message = Column(Text)
    welcome_enabled = Column(Boolean, default=False)
    
    # 退出メッセージ設定
    leave_channel_id = Column(String)
    leave_message = Column(Text)
    leave_enabled = Column(Boolean, default=False)
    
    # ロール設定
    auto_role_id = Column(String)
    auto_role_enabled = Column(Boolean, default=False)
    mod_role_ids = Column(ARRAY(String), default=[])
    
    # ログ設定
    log_channel_id = Column(String)
    log_enabled = Column(Boolean, default=False)
    log_message_delete = Column(Boolean, default=True)
    log_message_edit = Column(Boolean, default=True)
    log_member_join = Column(Boolean, default=True)
    log_member_leave = Column(Boolean, default=True)
    log_moderation_actions = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="settings")

class AIModSettings(Base):
    __tablename__ = 'ai_mod_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    
    # AI設定
    enabled = Column(Boolean, default=False)
    toxicity_threshold = Column(Float, default=0.8)
    identity_attack_threshold = Column(Float, default=0.8)
    insult_threshold = Column(Float, default=0.8)
    threat_threshold = Column(Float, default=0.9)
    sexual_threshold = Column(Float, default=0.9)
    custom_bad_words = Column(ARRAY(String), default=[])
    
    # アクション設定
    action_on_detect = Column(String, default='warn')  # warn, delete, mute, kick, ban
    mute_duration = Column(Integer, default=10)  # 分単位
    notify_mods = Column(Boolean, default=True)
    
    # 除外設定
    excluded_channels = Column(ARRAY(String), default=[])
    excluded_roles = Column(ARRAY(String), default=[])
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="ai_mod_settings")

class ModerationSettings(Base):
    __tablename__ = 'moderation_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    
    # 基本設定
    enabled = Column(Boolean, default=True)
    log_channel_id = Column(String)
    mod_role_ids = Column(ARRAY(String), default=[])
    admin_role_ids = Column(ARRAY(String), default=[])
    
    # 自動モデレーション設定
    auto_mod_enabled = Column(Boolean, default=True)
    filter_invites = Column(Boolean, default=True)
    filter_links = Column(Boolean, default=False)
    filter_swear_words = Column(Boolean, default=True)
    custom_filtered_words = Column(ARRAY(String), default=[])
    
    # 警告設定
    max_warnings = Column(Integer, default=3)
    warning_timeout = Column(Integer, default=30)  # 日数
    warning_action = Column(String, default='mute')  # mute, kick, ban
    
    # ミュート設定
    mute_role_id = Column(String)
    default_mute_time = Column(Integer, default=60)  # 分単位
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="moderation_settings")

class AutoResponseSettings(Base):
    __tablename__ = 'auto_response_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    
    # 基本設定
    enabled = Column(Boolean, default=False)
    response_chance = Column(Float, default=0.1)
    cooldown = Column(Integer, default=60)
    max_context_length = Column(Integer, default=10)
    
    # AI設定
    ai_enabled = Column(Boolean, default=False)
    ai_temperature = Column(Float, default=0.7)
    ai_persona = Column(Text, default='あなたはフレンドリーで役立つアシスタントです。')
    
    # 除外設定
    ignore_bots = Column(Boolean, default=True)
    ignore_prefixes = Column(ARRAY(String), default=['!', '?', '/', '.', '-'])
    
    # カスタム応答パターン
    custom_responses = Column(JSON, default={})
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="auto_response_settings")

class RaidSettings(Base):
    __tablename__ = 'raid_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    
    # 基本設定
    enabled = Column(Boolean, default=True)
    new_user_threshold = Column(Integer, default=10)  # X人の新規参加
    new_user_window = Column(Integer, default=10)     # Y秒以内
    
    # アクション設定
    action = Column(String, default='lockdown')      # alert, verification, lockdown
    lockdown_duration = Column(Integer, default=30)  # 分単位
    notify_admins = Column(Boolean, default=True)
    lockdown_channels = Column(Boolean, default=True)
    
    # 新規アカウント対策
    auto_kick_new_accounts = Column(Boolean, default=False)
    new_account_threshold = Column(Integer, default=1)  # アカウント作成からの日数
    
    # 通知設定
    alert_channel_id = Column(String)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="raid_settings")

class SpamSettings(Base):
    __tablename__ = 'spam_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), unique=True)
    
    # 基本設定
    enabled = Column(Boolean, default=True)
    message_threshold = Column(Integer, default=5)  # X個のメッセージ
    message_window = Column(Integer, default=5)     # Y秒以内
    
    # スパム検出の種類
    mention_threshold = Column(Integer, default=5)  # メンション数
    link_threshold = Column(Integer, default=3)     # リンク数
    emoji_threshold = Column(Integer, default=20)   # 絵文字数
    attachment_threshold = Column(Integer, default=5)  # 添付ファイル数
    
    # アクション設定
    action = Column(String, default='mute')  # warn, delete, mute, kick, ban
    mute_duration = Column(Integer, default=15)  # 分単位
    warn_before_mute = Column(Boolean, default=True)
    
    # 高度な設定
    smart_detection = Column(Boolean, default=True)  # パターン認識によるスマート検出
    excluded_channels = Column(ARRAY(String), default=[])
    excluded_roles = Column(ARRAY(String), default=[])
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="spam_settings")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String, nullable=False)
    target_id = Column(String)  # ユーザーID、ロールID、チャンネルIDなど
    target_type = Column(String)  # user, role, channel, settingなど
    details = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="logs")
    user = relationship("User", back_populates="logs")

class CustomCommand(Base):
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    name = Column(String, nullable=False)
    description = Column(Text)
    response = Column(Text, nullable=False)
    created_by = Column(String)
    uses_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーションシップ
    guild = relationship("Guild", back_populates="commands")

class WebhookLog(Base):
    """Webhookログ"""
    __tablename__ = 'webhook_logs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(20), nullable=False)
    webhook_url = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)
    content = Column(Text)
    success = Column(Boolean, default=True)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, event_type='{self.event_type}')>"

class ModerationAction(Base):
    """モデレーション実行履歴"""
    __tablename__ = 'moderation_actions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    moderator_id = Column(String(20), nullable=False)  # Discord User ID
    target_id = Column(String(20), nullable=False)     # Discord User ID
    action_type = Column(String(50), nullable=False)   # warn, mute, kick, ban
    reason = Column(Text)
    action_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    guild = relationship("Guild")
    infractions = relationship("UserInfraction", back_populates="action")
    
    def __repr__(self):
        return f"<ModerationAction(id={self.id}, type='{self.action_type}', target='{self.target_id}')>"

class UserInfraction(Base):
    """ユーザー違反履歴"""
    __tablename__ = 'user_infractions'
    
    id = Column(Integer, primary_key=True)
    action_id = Column(Integer, ForeignKey('moderation_actions.id'))
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    user_id = Column(String(20), nullable=False)      # Discord User ID
    moderator_id = Column(String(20), nullable=False) # Discord User ID
    action_type = Column(String(50), nullable=False)  # warn, mute, kick, ban
    reason = Column(Text)
    duration = Column(Integer)  # 分単位、Nullの場合は無期限
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # リレーションシップ
    guild = relationship("Guild")
    action = relationship("ModerationAction", back_populates="infractions")
    
    def __repr__(self):
        return f"<UserInfraction(id={self.id}, user='{self.user_id}', type='{self.action_type}')>" 