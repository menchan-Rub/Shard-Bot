from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Shard Bot API"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    VERSION: str = "0.1.0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Discord OAuth2
    DISCORD_CLIENT_ID: str = "1340998901255110756"  # あなたのBotのクライアントID
    DISCORD_CLIENT_SECRET: str = "YOUR_CLIENT_SECRET"  # Discord Developer Portalから取得
    DISCORD_REDIRECT_URI: str = "http://localhost:8080/auth/callback"
    DISCORD_SCOPES: List[str] = ["identify", "guilds"]
    
    # 許可するユーザー（Discord ID）
    ALLOWED_DISCORD_IDS: List[str] = [
        "YOUR_DISCORD_ID",  # あなたのDiscord ID
    ]
    
    # Database
    DB_TYPE: str = "sqlite"
    SQLITE_DB_FILE: str = "shardbot.db"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "shardbot"

    # Admin Account
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_EMAIL: Optional[str] = None

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            db_file = os.path.join(os.path.dirname(__file__), self.SQLITE_DB_FILE)
            return f"sqlite:///{db_file}"
        else:
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode=disable"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings() 