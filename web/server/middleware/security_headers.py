from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    セキュリティに関するHTTPヘッダーを追加するミドルウェア
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' https://cdn.discordapp.com; script-src 'self'; style-src 'self'; connect-src 'self'"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content-Type Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Frame Options (クリックジャッキング対策)
        response.headers["X-Frame-Options"] = "DENY"
        
        # Strict Transport Security (HTTPS強制)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Feature Policy
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        
        return response 