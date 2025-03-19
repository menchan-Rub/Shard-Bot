from jose import JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime, timedelta
import aiohttp
import uuid

from database.database import get_db
from models.user import User
from config import settings
from middleware.auth_middleware import (
    oauth,
    create_access_token,
    verify_access_token,
    verify_token,
)
from schemas.auth import Token, TokenData, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# OAuth2のスキーマ設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DISCORD_API_URL = "https://discord.com/api/v10"
DISCORD_AUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={settings.DISCORD_CLIENT_ID}&redirect_uri={settings.DISCORD_REDIRECT_URI}&response_type=code&scope={'%20'.join(settings.DISCORD_SCOPES)}"

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
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
    
    # ランダムなJTI（JWT ID）を追加して、トークンをユニークにする
    to_encode.update({"jti": str(uuid.uuid4())})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.get("/session")
async def get_session(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """現在のセッション情報を取得"""
    try:
        # トークンの検証
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # ユーザーIDの取得と検証
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # トークンの有効期限チェック
        if "exp" in payload:
            expiration = datetime.fromtimestamp(payload["exp"])
            if expiration < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="認証に失敗しました",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
        return {
            "status": "success",
            "data": {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "discord_id": user.discord_id,
                    "is_admin": user.is_admin,
                    # 認証トークンをレスポンスから削除
                    # "discord_access_token": user.discord_access_token
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
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
        print(f"Discord callback received with code: {code[:10]}...")
        # アクセストークンの取得
        token_url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.DISCORD_REDIRECT_URI
        }
        
        print(f"Using client_id: {settings.DISCORD_CLIENT_ID}")
        print(f"Using redirect_uri: {settings.DISCORD_REDIRECT_URI}")
        
        async with aiohttp.ClientSession() as session:
            print("Requesting token from Discord API...")
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    response_text = await response.text()
                    print(f"Discord API token request failed: {response.status}, {response_text}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Discord認証に失敗しました: {response_text}"
                    )
                token_data = await response.json()
                print("Token successfully received from Discord API")
                
            # ユーザー情報の取得
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            print("Requesting user info from Discord API...")
            async with session.get(f"{DISCORD_API_URL}/users/@me", headers=headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    print(f"Discord API user info request failed: {response.status}, {response_text}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"ユーザー情報の取得に失敗しました: {response_text}"
                    )
                user_data = await response.json()
                print(f"User info received: {user_data['username']}, ID: {user_data['id']}")
                
                # 許可されたユーザーかチェック
                allowed_ids = [id.strip() for id in settings.ALLOWED_DISCORD_IDS.split(",") if id.strip()]
                print(f"Allowed Discord IDs: {allowed_ids}")
                print(f"User ID to check: {user_data['id']}")
                
                if user_data["id"] not in allowed_ids:
                    print(f"User not in allowed list: {user_data['id']}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="このユーザーはアクセスを許可されていません"
                    )
                print("User authorized successfully")
                
                # ユーザーの作成または更新
                user = db.query(User).filter(User.discord_id == user_data["id"]).first()
                try:
                    if not user:
                        print(f"Creating new user for Discord ID: {user_data['id']}")
                        user = User(
                            discord_id=user_data["id"],
                            username=user_data["username"],
                            discord_access_token=token_data["access_token"],
                            discord_refresh_token=token_data.get("refresh_token"),
                            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
                        )
                        db.add(user)
                    else:
                        print(f"Updating existing user: {user.username}, ID: {user.id}")
                        user.discord_access_token = token_data["access_token"]
                        user.discord_refresh_token = token_data.get("refresh_token")
                        user.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
                        user.username = user_data["username"]
                    
                    db.commit()
                    print(f"Database commit successful for user ID: {user_data['id']}")
                    db.refresh(user)
                    print(f"User object refreshed with ID: {user.id}")
                    
                    # JWTトークンの生成
                    print(f"Generating JWT token for user ID: {user.id}")
                    access_token = create_access_token(
                        data={
                            "sub": str(user.id),
                            "discord_id": user.discord_id
                        }
                    )
                    print(f"JWT token generated successfully")
                    
                    return {
                        "access_token": access_token,
                        "token_type": "bearer",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "discord_id": user.discord_id
                        }
                    }
                except Exception as db_error:
                    print(f"Database operation error: {str(db_error)}")
                    db.rollback()
                    import traceback
                    print(f"Database error traceback: {traceback.format_exc()}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"データベース操作中にエラーが発生しました: {str(db_error)}"
                    )
                
    except HTTPException:
        print("HTTPException occurred, re-raising")
        raise
    except Exception as e:
        print(f"Unexpected error in Discord callback: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"認証処理でエラーが発生しました: {str(e)}"
        ) 