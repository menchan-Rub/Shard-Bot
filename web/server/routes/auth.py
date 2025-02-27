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

from web.server.database.database import get_db
from web.server.models.user import User
from web.server.config import settings
from web.server.middleware.auth_middleware import (
    oauth,
    get_current_user,
    create_access_token,
    verify_access_token,
)
from web.server.schemas.auth import Token, TokenData, UserCreate, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWTの設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """ユーザー名とパスワードでログイン"""
    try:
        print(f"Login attempt for username: {form_data.username}")
        
        # デバッグ用の出力
        print("Request received:", {
            "username": form_data.username,
            "password": "***"
        })
        
        # 管理者アカウントのチェック
        if form_data.username == "admin" and form_data.password == "admin":
            user = db.query(User).filter(User.username == "admin").first()
            
            if not user:
                user = User(
                    username="admin",
                    discord_id="admin",
                    is_admin=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # JWTトークンを生成
            access_token = create_access_token(data={"sub": user.discord_id})
            
            # デバッグ用の出力
            print("Login successful, returning token")
            
            return {
                "status": "success",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "is_admin": user.is_admin
                    }
                }
            }
        
        # デバッグ用の出力
        print("Invalid credentials")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWTトークンを生成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """現在のユーザーを取得"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        discord_id: str = payload.get("sub")
        if discord_id is None:
            raise credentials_exception
        token_data = TokenData(discord_id=discord_id)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.discord_id == token_data.discord_id).first()
    if user is None:
        raise credentials_exception
    return user 