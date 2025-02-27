from sqlalchemy import Column, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class Guild(Base):
    __tablename__ = "guilds"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True)
    name = Column(String)
    icon = Column(String, nullable=True)
    owner_id = Column(BigInteger)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    channels = relationship("Channel", back_populates="guild")
    roles = relationship("Role", back_populates="guild")
    warnings = relationship("Warning", back_populates="guild")
    spam_logs = relationship("SpamLog", back_populates="guild")
    commands = relationship("Command", back_populates="guild")
    messages = relationship("Message", back_populates="guild") 