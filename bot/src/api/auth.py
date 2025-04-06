"""
ユーザー認証とアクセス制御用の機能を提供します。
JWT（JSON Web Token）を使用してユーザー認証を行います。
"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from bot.src.db.database import get_db_session
from bot.src.db.models import User, Guild
from bot.src.utils.config import get_config

# 設定の読み込み
config = get_config()
JWT_SECRET_KEY = config.get("jwt", {}).get("secret_key", "default_secret_key")
JWT_ALGORITHM = config.get("jwt", {}).get("algorithm", "HS256")
JWT_EXPIRATION = config.get("jwt", {}).get("expiration_minutes", 30)

# OAuth2スキーマ
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_jwt_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT（JSON Web Token）を生成します。
    
    Args:
        data: トークンに含めるデータ
        expires_delta: トークンの有効期限（省略時はデフォルト値を使用）
    
    Returns:
        JWT文字列
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRATION))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    JWTを検証して内容を取得します。
    
    Args:
        token: JWT文字列
    
    Returns:
        トークンから取得したデータ
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db_session)) -> User:
    """
    現在のユーザーを取得します。
    
    Args:
        token: JWT文字列
        db: データベースセッション
    
    Returns:
        User: ユーザーオブジェクト
        
    Raises:
        HTTPException: ユーザーが見つからない場合
    """
    payload = decode_jwt_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンからユーザーIDを取得できません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データベースエラー: {str(e)}",
        )

async def verify_guild_access(guild_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db_session)) -> Guild:
    """
    ユーザーがサーバーへのアクセス権を持っているか検証します。
    
    Args:
        guild_id: サーバーID
        user: 現在のユーザー
        db: データベースセッション
    
    Returns:
        Guild: サーバーオブジェクト
        
    Raises:
        HTTPException: アクセス権がない場合
    """
    try:
        # サーバーを検索
        guild = db.query(Guild).filter(Guild.id == guild_id).first()
        if guild is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="サーバーが見つかりません",
            )
        
        # ユーザーがサーバー管理者かどうかを確認（ここでは簡略化されています）
        # 実際の実装では、DiscordのAPIを使用してユーザーの権限を取得するかデータベースに保存された権限を確認します
        user_guild = next((g for g in user.guilds if g.id == guild_id), None)
        if user_guild is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このサーバーへのアクセス権がありません",
            )
        
        # 管理者権限の確認
        # このロジックは実際の権限システムに合わせて調整する必要があります
        if not user.is_admin and not user_guild.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このサーバーの管理権限がありません",
            )
        
        return guild
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データベースエラー: {str(e)}",
        ) 