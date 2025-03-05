from jose import JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os
import httpx
from passlib.context import CryptContext
import bcrypt
import aiohttp

from web.server.database.database import get_db
from web.server.models.user import User
from web.server.config import settings
from web.server.middleware.auth_middleware import (
    oauth,
    create_access_token,
    verify_access_token,
    verify_token,
)
from web.server.schemas.auth import Token, TokenData, UserCreate, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# パスワードハッシュ化のための設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2のスキーマ設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DISCORD_API_URL = "https://discord.com/api/v10"
DISCORD_AUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={settings.DISCORD_CLIENT_ID}&redirect_uri={settings.DISCORD_REDIRECT_URI}&response_type=code&scope={'%20'.join(settings.DISCORD_SCOPES)}"

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証トークンが無効です"
            )

        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )

        return user

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが無効です"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

@router.get("/session")
async def get_session(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """現在のセッション情報を取得"""
    try:
        # トークンの検証
        payload = await verify_token(token)
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
            
        # トークンの有効期限チェック
        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Discord認証の有効期限が切れています"
            )
            
        return {
            "status": "success",
            "data": {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "discord_id": user.discord_id
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション検証でエラーが発生しました: {str(e)}"
        )

@router.get("/session-status")
async def get_session_status():
    """セッションステータスを取得（認証なし）"""
    return {
        "status": "success",
        "data": {
            "authenticated": False,
            "message": "認証されていません"
        }
    }

@router.get("/discord/url")
async def get_discord_auth_url():
    """Discord認証URLを取得"""
    return {
        "url": DISCORD_AUTH_URL
    }

@router.post("/discord/callback")
async def discord_callback(code: str = Form(...), db: Session = Depends(get_db)):
    """Discordコールバック処理"""
    try:
        # アクセストークンの取得
        token_url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.DISCORD_REDIRECT_URI
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Discord認証に失敗しました"
                    )
                token_data = await response.json()
                
            # ユーザー情報の取得
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            async with session.get(f"{DISCORD_API_URL}/users/@me", headers=headers) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="ユーザー情報の取得に失敗しました"
                    )
                user_data = await response.json()
                
                # 許可されたユーザーかチェック
                if user_data["id"] not in settings.ALLOWED_DISCORD_IDS:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="このユーザーはアクセスを許可されていません"
                    )
                
                # ユーザーの作成または更新
                user = db.query(User).filter(User.discord_id == user_data["id"]).first()
                if not user:
                    user = User(
                        discord_id=user_data["id"],
                        username=user_data["username"],
                        discord_access_token=token_data["access_token"],
                        discord_refresh_token=token_data.get("refresh_token"),
                        token_expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
                    )
                    db.add(user)
                else:
                    user.discord_access_token = token_data["access_token"]
                    user.discord_refresh_token = token_data.get("refresh_token")
                    user.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
                    user.username = user_data["username"]
                
                db.commit()
                db.refresh(user)
                
                # JWTトークンの生成
                access_token = create_access_token(
                    data={
                        "sub": str(user.id),
                        "discord_id": user.discord_id
                    }
                )
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "discord_id": user.discord_id
                    }
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"認証処理でエラーが発生しました: {str(e)}"
        )

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """ユーザーログイン"""
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザー名またはパスワードが間違っています"
            )
        
        if not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザー名またはパスワードが間違っています"
            )
        
        # アクセストークンの生成
        access_token = create_access_token(
            data={"user_id": user.id}  # usernameではなくidを使用
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_admin": user.is_admin
            }
        }
        
    except Exception as e:
        raise 