import os
import sys
from pathlib import Path

# プロジェクトルートディレクトリをPythonパスに追加
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
from web.server.routes.guilds import router as guilds_router
from web.server.middleware.error_handler import handle_errors
from web.server.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=True
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# デバッグ用のミドルウェア
@app.middleware("http")
async def debug_middleware(request, call_next):
    print(f"\n--- Incoming request ---")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {request.headers}")
    
    response = await call_next(request)
    
    print(f"\n--- Outgoing response ---")
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
    return response

# エラーハンドラーの設定
app.middleware("http")(handle_errors)

# ルーターの登録
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(logs_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(channels_router)
app.include_router(analytics_router)
app.include_router(guilds_router)

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "Welcome to Shard Bot API",
        "version": settings.VERSION
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("FastAPIサーバーを起動します...")
    print(f"Host: 0.0.0.0")
    print(f"Port: 8000")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )