from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base

class SpamLog(Base):
    __tablename__ = "spam_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    channel_id = Column(BigInteger, ForeignKey("channels.id"))
    user_id = Column(BigInteger)
    message_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    guild = relationship("Guild", back_populates="spam_logs")
    channel = relationship("Channel", back_populates="spam_logs") 