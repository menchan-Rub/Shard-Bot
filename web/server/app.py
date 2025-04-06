from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import os
import sys
import logging
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import uvicorn

# ルートパスを調整してbotのモジュールにアクセスできるようにする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# 環境変数のロード
load_dotenv()

# データベース接続のインポート
from bot.src.db.database import get_db_session, init_db, create_tables_if_not_exist
from bot.src.db.models import (
    User, UserSession, Guild, GuildSettings,
    ModerationSettings, AutoResponseSettings,
    RaidSettings, SpamSettings, AuditLog
)

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("api")

# FastAPIアプリの作成
app = FastAPI(
    title="Shard Bot API",
    description="Discord Shard Bot管理用API",
    version="1.0.0"
)

# CORSの設定
origins = [
    os.getenv("WEB_DASHBOARD_URL", "http://localhost:3000"),
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:4000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルートのインポート - 現在存在するルートのみインポート
try:
    from bot.src.api.routes import auth, settings
    
    # ルーターの登録
    app.include_router(auth.router)
    app.include_router(settings.router)
    # 他のルーターは実装後に追加します
    # app.include_router(guilds.router)
    # app.include_router(moderation.router)
    # app.include_router(raid.router)
    # app.include_router(spam.router)
    # app.include_router(auto_response.router)
    # app.include_router(logs.router)
    # app.include_router(stats.router)
except ImportError as e:
    logger.error(f"APIルートのインポートに失敗しました: {e}")

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("APIサーバーを起動しています...")
    try:
        # データベーステーブルの作成
        result = await create_tables_if_not_exist()
        if result:
            logger.info("データベースの初期化が完了しました")
    except Exception as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("APIサーバーをシャットダウンしています...")

@app.get("/", tags=["ヘルスチェック"])
async def root():
    """ルートエンドポイント"""
    return {"message": "Shard Bot API サーバーが正常に動作しています"}

@app.get("/health", tags=["ヘルスチェック"])
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # データベース接続の確認
        with get_db_session() as session:
            session.execute("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )

# アプリケーションの直接実行
if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True) 