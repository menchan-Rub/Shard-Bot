from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # アプリケーション設定
    APP_NAME: str = "ShardBot API"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # データベース設定
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "shardbot"
    
    # JWT設定
    JWT_SECRET_KEY: str = "your-secret-key"  # 本番環境では必ず変更してください
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Discord設定
    DISCORD_CLIENT_ID: Optional[str] = None
    DISCORD_CLIENT_SECRET: Optional[str] = None
    DISCORD_REDIRECT_URI: str = "http://localhost:3000/auth/callback"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 