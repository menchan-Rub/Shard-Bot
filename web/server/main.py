import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from web.server.database.database import get_db
from web.server.routes.auth import router as auth_router
from web.server.routes.settings import router as settings_router
from web.server.routes.logs import router as logs_router
from web.server.routes.users import router as users_router
from web.server.routes.roles import router as roles_router
from web.server.routes.channels import router as channels_router
from web.server.routes.analytics import router as analytics_router
from web.server.middleware.error_handler import handle_errors

app = FastAPI(
    title="ShardBot Dashboard API",
    description="ShardBot管理用ダッシュボードのバックエンドAPI",
    version="1.0.0"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# エラーハンドラーの設定
app.middleware("http")(handle_errors)

# ルーターの登録
app.include_router(auth_router, prefix="/api/auth", tags=["認証"])
app.include_router(settings_router, prefix="/api/settings", tags=["設定"])
app.include_router(logs_router, prefix="/api/logs", tags=["ログ"])
app.include_router(users_router, prefix="/api/users", tags=["ユーザー"])
app.include_router(roles_router, prefix="/api/roles", tags=["ロール"])
app.include_router(channels_router, prefix="/api/channels", tags=["チャンネル"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["分析"])

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Welcome to ShardBot API"}

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
        "main:app",
        host=host,
        port=port,
        reload=True,
        workers=4
    )