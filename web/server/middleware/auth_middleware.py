from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
import aiohttp

from config import settings

security = HTTPBearer()

DISCORD_API_URL = "https://discord.com/api/v10"
DISCORD_TOKEN_URL = f"{DISCORD_API_URL}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_URL}/users/@me"

async def oauth(code: str) -> dict:
    """Discordのアクセストークンを取得し、ユーザー情報を返します"""
    async with aiohttp.ClientSession() as session:
        # アクセストークンの取得
        data = {
            'client_id': settings.DISCORD_CLIENT_ID,
            'client_secret': settings.DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.DISCORD_REDIRECT_URI
        }
        async with session.post(DISCORD_TOKEN_URL, data=data) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get Discord access token"
                )
            token_data = await response.json()

        # ユーザー情報の取得
        headers = {'Authorization': f"Bearer {token_data['access_token']}"}
        async with session.get(DISCORD_USER_URL, headers=headers) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get Discord user info"
                )
            user_data = await response.json()

        return {
            'discord_id': user_data['id'],
            'username': user_data['username'],
            'avatar': user_data.get('avatar'),
            'access_token': token_data['access_token']
        }

async def verify_access_token(token: str) -> dict:
    """Discordのアクセストークンを検証し、ユーザー情報を返します"""
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f"Bearer {token}"}
        async with session.get(DISCORD_USER_URL, headers=headers) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Discord access token"
                )
            user_data = await response.json()
            return user_data

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        ) 