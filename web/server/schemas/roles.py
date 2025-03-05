from pydantic import BaseModel
from typing import List, Optional

class RoleResponse(BaseModel):
    id: str
    name: str
    color: str
    hoist: bool
    position: int
    permissions: str
    mentionable: bool
    member_count: int

class RoleList(BaseModel):
    roles: List[RoleResponse]
    total: int
    page: int
    limit: int

    class Config:
        from_attributes = True 