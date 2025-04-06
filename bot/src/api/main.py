"""
Discordボット用のAPIメインファイル
FastAPIを使用して、ボットの管理用APIエンドポイントを提供します。
"""
import logging
import os
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from bot.src.api.auth import get_current_user, verify_guild_access
from bot.src.api.models import (
    UserResponse, GuildResponse, TokenRequest, TokenResponse,
    InfractionResponse, ModerationSettingsResponse, RaidProtectionSettingsResponse,
    AntiSpamSettingsResponse, AutoResponsePatternResponse, AutoResponseSettingsResponse
)
from bot.src.db.database import get_db_session
from bot.src.utils.config import get_config

# ロガーの設定
logger = logging.getLogger('api')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# APIアプリケーションの作成
app = FastAPI(
    title="Shard Bot API",
    description="Discord Bot管理用API",
    version="1.0.0",
)

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエスト処理時間ミドルウェア
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# エラーハンドラー
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# ルートエンドポイント
@app.get("/")
async def root():
    return {
        "name": "Shard Bot API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# ルートのインポート
from bot.src.api.routes.auth import router as auth_router
from bot.src.api.routes.moderation import router as moderation_router
from bot.src.api.routes.raid_protection import router as raid_protection_router
from bot.src.api.routes.anti_spam import router as anti_spam_router
from bot.src.api.routes.auto_response import router as auto_response_router
from bot.src.api.routes.settings import router as settings_router

# ルートの登録
app.include_router(auth_router, prefix="/auth", tags=["認証"])
app.include_router(moderation_router, prefix="/moderation", tags=["モデレーション"])
app.include_router(raid_protection_router, prefix="/raid-protection", tags=["レイド対策"])
app.include_router(anti_spam_router, prefix="/anti-spam", tags=["アンチスパム"])
app.include_router(auto_response_router, prefix="/auto-response", tags=["自動応答"])
app.include_router(settings_router, prefix="/settings", tags=["設定"])

# APIの起動
if __name__ == "__main__":
    config = get_config()
    host = config.get("api", {}).get("host", "0.0.0.0")
    port = config.get("api", {}).get("port", 8000)
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "bot.src.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    ) 