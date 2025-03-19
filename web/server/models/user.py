from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # テーブルの再定義を許可

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)  # Discordのユーザー名
    discord_id = Column(String, unique=True, index=True)  # Discordのユーザーid
    discord_access_token = Column(Text)  # Discordのアクセストークン
    discord_refresh_token = Column(Text)  # Discordのリフレッシュトークン
    token_expires_at = Column(DateTime(timezone=True))  # トークンの有効期限
    is_admin = Column(Boolean, default=False)  # 管理者フラグ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # リレーションシップの定義
    # settings = relationship("Settings", back_populates="user", uselist=False)
    bot_settings = relationship("BotSettings", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    user_warnings = relationship("Warning", back_populates="user")
    commands = relationship("Command", back_populates="user")
    messages = relationship("Message", back_populates="user") 