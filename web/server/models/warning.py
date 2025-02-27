from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class Warning(Base):
    __tablename__ = "warnings"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    moderator_id = Column(BigInteger)
    reason = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    guild = relationship("Guild", back_populates="warnings")
    user = relationship("User", back_populates="user_warnings") 