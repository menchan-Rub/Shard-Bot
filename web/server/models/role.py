from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from database.database import Base

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"))
    discord_id = Column(String, unique=True, index=True)
    name = Column(String)
    color = Column(Integer)
    position = Column(Integer)
    permissions = Column(BigInteger)

    # Relationships
    guild = relationship("Guild", back_populates="roles") 