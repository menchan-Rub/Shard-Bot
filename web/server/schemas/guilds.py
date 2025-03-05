from pydantic import BaseModel
from typing import List, Optional

class GuildResponse(BaseModel):
    id: str
    name: str
    icon: Optional[str]
    owner: bool
    permissions: str

class GuildList(BaseModel):
    guilds: List[GuildResponse]

    class Config:
        from_attributes = True 