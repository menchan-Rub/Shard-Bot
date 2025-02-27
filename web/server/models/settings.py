from sqlalchemy import Column, BigInteger, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship

from web.server.database.database import Base

class Settings(Base):
    __tablename__ = "settings"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    notifications = Column(Boolean, default=True)
    theme = Column(String, default="light")
    language = Column(String, default="en")

    # Relationships
    user = relationship("User", back_populates="settings") 