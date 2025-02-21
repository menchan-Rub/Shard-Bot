from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Guild(Base):
    """サーバー設定を保存するテーブル"""
    __tablename__ = 'guilds'
    
    id = Column(BigInteger, primary_key=True)
    prefix = Column(String(10), default='!')
    language = Column(String(5), default='ja')
    mod_role_id = Column(BigInteger)
    admin_role_id = Column(BigInteger)
    log_channel_id = Column(BigInteger)
    welcome_channel_id = Column(BigInteger)
    welcome_message = Column(Text)
    leave_message = Column(Text)
    spam_protection = Column(Boolean, default=True)
    raid_protection = Column(Boolean, default=True)
    support_guild_id = Column(BigInteger)  # サポートスタッフ用のサーバーID
    support_category_id = Column(BigInteger)  # サポートチケット用のカテゴリーID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    """ユーザー情報を保存するテーブル"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    warnings = Column(Integer, default=0)
    is_blacklisted = Column(Boolean, default=False)
    last_message_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Warning(Base):
    """警告履歴を保存するテーブル"""
    __tablename__ = 'warnings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    moderator_id = Column(BigInteger)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SpamLog(Base):
    """スパム検出ログを保存するテーブル"""
    __tablename__ = 'spam_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    channel_id = Column(BigInteger)
    message_content = Column(Text)
    detection_type = Column(String(50))  # spam, raid, etc.
    action_taken = Column(String(50))  # warn, mute, kick, ban
    created_at = Column(DateTime, default=datetime.utcnow)

class Timer(Base):
    """タイマー情報を保存するテーブル"""
    __tablename__ = 'timers'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    channel_id = Column(BigInteger)
    user_id = Column(BigInteger)
    expires_at = Column(DateTime)
    message = Column(Text)
    is_recurring = Column(Boolean, default=False)
    interval = Column(Integer)  # 繰り返し間隔（秒）
    created_at = Column(DateTime, default=datetime.utcnow)

class CustomCommand(Base):
    """カスタムコマンドを保存するテーブル"""
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    name = Column(String(100))
    response = Column(Text)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AutoMod(Base):
    """自動モデレーション設定を保存するテーブル"""
    __tablename__ = 'automod'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    rule_type = Column(String(50))  # spam, raid, regex, etc.
    rule_data = Column(JSON)  # 具体的な設定をJSON形式で保存
    is_enabled = Column(Boolean, default=True)
    action = Column(String(50))  # warn, mute, kick, ban
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    """監査ログを保存するテーブル"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    action_type = Column(String(50))
    user_id = Column(BigInteger)
    target_id = Column(BigInteger)
    reason = Column(Text)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportTicket(Base):
    """サポートチケット情報を保存するテーブル"""
    __tablename__ = 'support_tickets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    admin_channel_id = Column(BigInteger)
    webhook1_url = Column(String(255))
    webhook2_url = Column(String(255))
    name = Column(String(50))
    service = Column(String(100))
    is_bug = Column(Boolean)
    severity = Column(String(10))
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 