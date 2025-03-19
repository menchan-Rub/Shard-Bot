from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from database.database import Base

class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    discord_id = Column(String, unique=True, index=True)
    name = Column(String)
    type = Column(String)
    position = Column(Integer)
    topic = Column(String, nullable=True)
    is_nsfw = Column(Boolean, default=False)

    # Relationships
    guild = relationship("Guild", back_populates="channels")
    spam_logs = relationship("SpamLog", back_populates="channel")
    messages = relationship("Message", back_populates="channel") 