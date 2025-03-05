from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # テーブルの再定義を許可

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    discord_id = Column(String, unique=True, index=True)
    discord_access_token = Column(Text)
    discord_refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # リレーションシップの定義
    settings = relationship("Settings", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")
    user_warnings = relationship("Warning", back_populates="user")
    commands = relationship("Command", back_populates="user")
    messages = relationship("Message", back_populates="user") 