from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import os
import secrets
from sqlalchemy.orm import Session
import logging
import redis
import json

from bot.src.db.database import get_db_session, get_redis_url
from bot.src.db.models import User, UserSession
from bot.src.db.repository import GuildRepository

# ロガー設定
logger = logging.getLogger('api.auth')

# Redis接続
redis_client = redis.from_url(get_redis_url())

# ルーター設定
router = APIRouter(
    prefix="/auth",
    tags=["認証"],
    responses={401: {"description": "未認証"}}
)

# JWT設定
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key_here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "86400"))  # デフォルト24時間

# OAuth2パスワードフロー
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# リクエスト/レスポンスモデル
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class TokenData(BaseModel):
    user_id: Optional[str] = None

class UserCreate(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None

# ヘルパー関数
def create_access_token(data: dict, expires_delta: timedelta = None):
    """JWTトークンを生成する"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """JWTトークンからユーザーを取得"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # トークンを検証
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Redisからユーザー情報を取得（キャッシュ）
        user_key = f"user:{user_id}"
        user_data = redis_client.get(user_key)
        
        if user_data:
            # キャッシュから取得
            return json.loads(user_data)
        else:
            # データベースから取得
            with get_db_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user is None:
                    raise credentials_exception
                
                # ユーザー情報を辞書に変換
                user_dict = {
                    "id": user.id,
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "is_admin": user.is_admin
                }
                
                # Redisにキャッシュ (10分間)
                redis_client.setex(user_key, 600, json.dumps(user_dict))
                
                return user_dict
    except jwt.PyJWTError:
        raise credentials_exception

# エンドポイント
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """アクセストークンを取得"""
    # Discord OAuthからのデータを想定
    # 実際のImplementationではDiscord OAuthを使用し、form_dataをDiscordから取得する
    
    with get_db_session() as session:
        # ユーザーを検索または作成
        user = session.query(User).filter(User.user_id == form_data.username).first()
        
        if not user:
            # 新規ユーザーとして登録（本来はDiscord APIからデータ取得）
            user = User(
                user_id=form_data.username,
                username=form_data.username,
                is_active=True
            )
            session.add(user)
            session.commit()
        
        # セッション情報を記録
        session_token = secrets.token_hex(32)
        expires_at = datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
        
        db_session = UserSession(
            user_id=user.id,
            token=session_token,
            expires_at=expires_at
        )
        session.add(db_session)
        
        # 最終ログイン時間を更新
        user.last_login = datetime.utcnow()
        session.commit()
        
        # アクセストークンを生成
        access_token_expires = timedelta(seconds=JWT_EXPIRATION)
        access_token = create_access_token(
            data={"sub": user.user_id}, expires_delta=access_token_expires
        )
        
        # ユーザー情報を辞書に変換
        user_dict = {
            "id": user.id,
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "is_admin": user.is_admin
        }
        
        # Redisにキャッシュ (10分間)
        user_key = f"user:{user.user_id}"
        redis_client.setex(user_key, 600, json.dumps(user_dict))
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION,
            "user": user_dict
        }

@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """ログアウト処理"""
    try:
        # TokenからセッションIDを取得
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Redisからユーザー情報を削除
            user_id = current_user.get("user_id")
            if user_id:
                user_key = f"user:{user_id}"
                redis_client.delete(user_key)
            
            # ブラックリストにトークンを追加（無効化）
            token_blacklist_key = f"blacklist:token:{token}"
            redis_client.setex(
                token_blacklist_key, 
                JWT_EXPIRATION,  # トークンの有効期限分だけブラックリストに保持
                "1"
            )
            
            return {"message": "ログアウトに成功しました"}
    except Exception as e:
        logger.error(f"ログアウト中にエラーが発生: {e}")
        
    return {"message": "ログアウトに成功しました"}

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return current_user

@router.get("/guilds")
async def get_user_guilds(current_user: dict = Depends(get_current_user)):
    """ユーザーのギルド一覧を取得"""
    # 実際のImplementationではDiscord APIからユーザーのギルド一覧を取得する
    # ここではサンプルデータを返す
    return {
        "guilds": [
            {
                "id": "123456789012345678",
                "name": "サンプルサーバー",
                "icon": "https://cdn.discordapp.com/icons/123456789012345678/abcdef.png",
                "owner": True,
                "permissions": "2147483647"
            }
        ]
    } 