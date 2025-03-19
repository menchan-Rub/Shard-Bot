import os
import sys
from pathlib import Path

# プロジェクトルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database.database import get_db, init_db
from routes.auth import router as auth_router
from routes.settings import router as settings_router
from routes.logs import router as logs_router
from routes.users import router as users_router
from routes.roles import router as roles_router
from routes.channels import router as channels_router
from routes.analytics import router as analytics_router
from routes.guilds import router as guilds_router
from middleware.error_handler import handle_errors
from middleware.rate_limiter import RateLimiter
from middleware.security_headers import SecurityHeadersMiddleware
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# データベースの初期化
@app.on_event("startup")
async def startup_event():
    print("Initializing database...")
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# セキュリティヘッダーの適用
app.add_middleware(SecurityHeadersMiddleware)

# レート制限の適用
app.add_middleware(RateLimiter)

# CORS設定
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# デバッグ用のミドルウェア（開発環境のみ）
if settings.DEBUG:
    @app.middleware("http")
    async def debug_middleware(request, call_next):
        print(f"\n--- Incoming request ---")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        print(f"Headers: {request.headers}")
        
        try:
            response = await call_next(request)
            
            print(f"\n--- Outgoing response ---")
            print(f"Status: {response.status_code}")
            print(f"Headers: {response.headers}")
            return response
        except Exception as e:
            print(f"\n--- Exception occurred ---")
            print(f"Error: {str(e)}")
            print(f"Type: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise

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