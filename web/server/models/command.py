from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class Command(Base):
    __tablename__ = "commands"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    name = Column(String)
    args = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    guild = relationship("Guild", back_populates="commands")
    user = relationship("User", back_populates="commands") 