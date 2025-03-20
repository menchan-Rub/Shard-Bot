import time
from typing import Dict, Tuple, Any
import os
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        # 基本レート制限
        self.requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS", "300"))
        # 分析用の高いレート制限
        self.analytics_requests_per_minute = int(os.getenv("ANALYTICS_RATE_LIMIT", "500"))
        # 認証済みユーザー用の制限
        self.auth_requests_per_minute = int(os.getenv("AUTH_RATE_LIMIT", "400"))
        self.window = 60  # 1分間のウィンドウ
        # {ip: {"default": (request_count, window_start), "analytics": (request_count, window_start)}}
        self.clients: Dict[str, Dict[str, Tuple[int, float]]] = {}

    async def dispatch(self, request: Request, call_next):
        # リクエスト元のIPアドレスを取得
        ip = request.client.host if request.client else "unknown"
        
        # パスからリクエストタイプを決定
        path = request.url.path
        request_type = "analytics" if path.startswith("/analytics") else "default"
        
        # 認証情報の確認（トークンがあれば認証済みユーザーとみなす）
        is_authenticated = "Authorization" in request.headers
        
        # リクエストタイプに応じたレート制限を設定
        limit = self.requests_per_minute  # デフォルト制限
        if request_type == "analytics":
            limit = self.analytics_requests_per_minute
        elif is_authenticated:
            limit = self.auth_requests_per_minute
        
        # レート制限をチェック
        current_time = time.time()
        
        # IPアドレスのエントリを初期化
        if ip not in self.clients:
            self.clients[ip] = {}
            
        # リクエストタイプのエントリを初期化
        if request_type not in self.clients[ip]:
            self.clients[ip][request_type] = (0, current_time)
            
        requests, window_start = self.clients[ip][request_type]
        
        # ウィンドウがリセットされるべきかチェック
        if current_time - window_start > self.window:
            # 新しいウィンドウを開始
            self.clients[ip][request_type] = (1, current_time)
        else:
            # 既存のウィンドウ内でリクエスト数を増加
            requests += 1
            if requests > limit:
                # レート制限を超過
                remaining = 0
                reset = int(window_start + self.window - current_time)
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "status": "error",
                        "message": "リクエスト数が制限を超えています。しばらく経ってから再試行してください。",
                        "limit": limit,
                        "reset_in_seconds": reset
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset),
                        "Retry-After": str(reset)
                    }
                )
            self.clients[ip][request_type] = (requests, window_start)
        
        # レート制限ヘッダーを追加
        response = await call_next(request)
        
        # 残りのリクエスト数とリセットまでの時間をヘッダーに設定
        if ip in self.clients and request_type in self.clients[ip]:
            requests, window_start = self.clients[ip][request_type]
            remaining = max(0, limit - requests)
            reset = int(window_start + self.window - current_time)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response 