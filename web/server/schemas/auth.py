from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserAuth(BaseModel):
    username: str
    discord_id: str
    avatar: str | None = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    discord_id: str
    avatar: str | None = None
    is_admin: bool = False

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    discord_id: str
    avatar: str | None = None
    is_admin: bool

    class Config:
        from_attributes = True 