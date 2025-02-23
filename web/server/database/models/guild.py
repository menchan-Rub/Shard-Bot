"""
Guild model for the ShardBot Dashboard API
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base

class Guild(Base):
    """Guild model representing a Discord server"""
    __tablename__ = 'guilds'

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    icon_url = Column(String)
    owner_id = Column(String, nullable=False)
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 