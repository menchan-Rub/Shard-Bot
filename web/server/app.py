from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import os

from .database import get_db
from .routes import auth, settings, logs, users, roles, channels, analytics
from .middleware import error_handler, auth_middleware

app = FastAPI(
    title="ShardBot Dashboard API",
    description="ShardBot管理用ダッシュボードのバックエンドAPI",
    version="1.0.0"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# エラーハンドラーの設定
app.middleware("http")(error_handler.handle_errors)

# ルーターの登録
app.include_router(auth.router, prefix="/api/auth", tags=["認証"])
app.include_router(settings.router, prefix="/api/settings", tags=["設定"])
app.include_router(logs.router, prefix="/api/logs", tags=["ログ"])
app.include_router(users.router, prefix="/api/users", tags=["ユーザー"])
app.include_router(roles.router, prefix="/api/roles", tags=["ロール"])
app.include_router(channels.router, prefix="/api/channels", tags=["チャンネル"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["分析"])

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "ShardBot Dashboard API"}

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}

if __name__ == "__main__":
    # 環境変数から設定を読み込み
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    # サーバーを起動
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True,
        workers=4
    ) 