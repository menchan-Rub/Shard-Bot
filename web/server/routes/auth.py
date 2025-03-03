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

from web.server.database.database import get_db
from web.server.models.user import User
from web.server.config import settings
from web.server.middleware.auth_middleware import (
    oauth,
    create_access_token,
    verify_access_token,
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
async def get_session(current_user: User = Depends(get_current_user)):
    """現在のセッション情報を取得"""
    return {
        "status": "success",
        "data": {
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "is_admin": current_user.is_admin
            }
        }
    }

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

@router.post("/discord/url")
async def get_discord_oauth_url():
    """Discordの認証URLを取得"""
    client_id = os.getenv("DISCORD_CLIENT_ID")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
    scope = "identify guilds"
    
    url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
    return {"url": url}

@router.get("/discord/callback")
async def discord_callback(code: str, db: Session = Depends(get_db)):
    """Discordのコールバック処理"""
    try:
        # アクセストークンを取得
        token_url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": os.getenv("DISCORD_CLIENT_ID"),
            "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.getenv("DISCORD_REDIRECT_URI")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            token_data = response.json()
            
            # ユーザー情報を取得
            headers = {
                "Authorization": f"Bearer {token_data['access_token']}"
            }
            user_response = await client.get("https://discord.com/api/users/@me", headers=headers)
            user_data = user_response.json()
            
            # ユーザーを作成または更新
            user = db.query(User).filter(User.discord_id == user_data["id"]).first()
            if not user:
                user = User(
                    discord_id=user_data["id"],
                    username=user_data["username"],
                    email=user_data.get("email"),
                    avatar=user_data.get("avatar")
                )
                db.add(user)
            else:
                user.username = user_data["username"]
                user.email = user_data.get("email")
                user.avatar = user_data.get("avatar")
            
            db.commit()
            
            # JWTトークンを生成
            access_token = create_access_token(data={"sub": user.discord_id})
            return {"access_token": access_token, "token_type": "bearer"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="認証に失敗しました"
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