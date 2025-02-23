"""
Bot model for the ShardBot Dashboard API
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base

class Bot(Base):
    """Bot model representing a Discord bot instance"""
    __tablename__ = 'bots'

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    avatar_url = Column(String)
    is_online = Column(Boolean, default=False)
    status = Column(String, default='offline')
    guild_count = Column(Integer, default=0)
    shard_count = Column(Integer, default=1)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 