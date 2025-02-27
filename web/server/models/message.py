from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    channel_id = Column(BigInteger, ForeignKey("channels.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    guild = relationship("Guild", back_populates="messages")
    channel = relationship("Channel", back_populates="messages")
    user = relationship("User", back_populates="messages") 