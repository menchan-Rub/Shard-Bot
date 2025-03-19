from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base

class BotSettings(Base):
    """ボットの設定モデル"""
    __tablename__ = "bot_settings"
    __table_args__ = {'extend_existing': True}  # テーブルの再定義を許可
    
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    user = relationship("User", back_populates="bot_settings")
    
    def __repr__(self):
        return f"<BotSettings(id={self.id}, guild_id={self.guild_id})>" 