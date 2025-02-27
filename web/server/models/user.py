from sqlalchemy import Column, String, BigInteger, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True)
    username = Column(String)
    discriminator = Column(String)
    avatar = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    settings = relationship("Settings", back_populates="user", uselist=False)
    user_warnings = relationship("Warning", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    commands = relationship("Command", back_populates="user")
    messages = relationship("Message", back_populates="user") 