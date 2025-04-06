from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime
import logging

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, AutoResponse
from bot.src.api.auth import get_current_user, verify_guild_access
from bot.src.api.models import AutoResponseCreate, AutoResponseUpdate, AutoResponseResponse

# ルーターの作成
router = APIRouter(
    prefix="/api/auto-responses",
    tags=["auto-responses"],
    responses={404: {"description": "Not found"}},
)

# ロガーの設定
logger = logging.getLogger("api.auto_response")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 自動応答の一覧取得
@router.get("/guilds/{guild_id}", response_model=List[AutoResponseResponse])
async def get_auto_responses(
    guild_id: str = Path(..., description="Discord Guild ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの自動応答一覧を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # 自動応答を取得
            auto_responses = session.query(AutoResponse).filter(
                AutoResponse.guild.has(discord_id=guild_id)
            ).order_by(
                AutoResponse.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            # レスポンスリストを構築
            result = []
            for ar in auto_responses:
                result.append(AutoResponseResponse(
                    id=ar.id,
                    guild_id=guild_id,
                    trigger=ar.trigger,
                    response=ar.response,
                    response_type=ar.response_type,
                    match_type=ar.match_type,
                    enabled=ar.enabled,
                    cooldown=ar.cooldown,
                    chance=ar.chance,
                    ignore_case=ar.ignore_case,
                    allowed_channels=ar.allowed_channels,
                    ignored_channels=ar.ignored_channels,
                    allowed_roles=ar.allowed_roles,
                    ignored_roles=ar.ignored_roles,
                    wildcard=ar.wildcard,
                    created_at=ar.created_at,
                    updated_at=ar.updated_at
                ))
            
            return result
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 自動応答の取得
@router.get("/guilds/{guild_id}/responses/{response_id}", response_model=AutoResponseResponse)
async def get_auto_response(
    guild_id: str = Path(..., description="Discord Guild ID"),
    response_id: str = Path(..., description="Auto Response ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの特定の自動応答を取得
    """
    # ギルドへのアクセス権を確認
    await verify_guild_access(current_user, guild_id)
    
    try:
        with get_db_session() as session:
            # 自動応答を取得
            ar = session.query(AutoResponse).filter(
                AutoResponse.id == response_id,
                AutoResponse.guild.has(discord_id=guild_id)
            ).first()
            
            if not ar:
                raise HTTPException(status_code=404, detail="Auto response not found")
            
            # レスポンスを返す
            return AutoResponseResponse(
                id=ar.id,
                guild_id=guild_id,
                trigger=ar.trigger,
                response=ar.response,
                response_type=ar.response_type,
                match_type=ar.match_type,
                enabled=ar.enabled,
                cooldown=ar.cooldown,
                chance=ar.chance,
                ignore_case=ar.ignore_case,
                allowed_channels=ar.allowed_channels,
                ignored_channels=ar.ignored_channels,
                allowed_roles=ar.allowed_roles,
                ignored_roles=ar.ignored_roles,
                wildcard=ar.wildcard,
                created_at=ar.created_at,
                updated_at=ar.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 自動応答の作成
@router.post("/guilds/{guild_id}", response_model=AutoResponseResponse)
async def create_auto_response(
    auto_response: AutoResponseCreate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーに新しい自動応答を作成
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # サーバー情報を取得
            guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
            if not guild:
                raise HTTPException(status_code=404, detail="Guild not found")
            
            # 新しい自動応答を作成
            new_ar = AutoResponse(
                guild_id=guild.id,
                trigger=auto_response.trigger,
                response=auto_response.response,
                response_type=auto_response.response_type,
                match_type=auto_response.match_type,
                enabled=auto_response.enabled,
                cooldown=auto_response.cooldown,
                chance=auto_response.chance,
                ignore_case=auto_response.ignore_case,
                allowed_channels=auto_response.allowed_channels,
                ignored_channels=auto_response.ignored_channels,
                allowed_roles=auto_response.allowed_roles,
                ignored_roles=auto_response.ignored_roles,
                wildcard=auto_response.wildcard,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # データベースに追加
            session.add(new_ar)
            session.commit()
            
            # 作成された自動応答を返す
            return AutoResponseResponse(
                id=new_ar.id,
                guild_id=guild_id,
                trigger=new_ar.trigger,
                response=new_ar.response,
                response_type=new_ar.response_type,
                match_type=new_ar.match_type,
                enabled=new_ar.enabled,
                cooldown=new_ar.cooldown,
                chance=new_ar.chance,
                ignore_case=new_ar.ignore_case,
                allowed_channels=new_ar.allowed_channels,
                ignored_channels=new_ar.ignored_channels,
                allowed_roles=new_ar.allowed_roles,
                ignored_roles=new_ar.ignored_roles,
                wildcard=new_ar.wildcard,
                created_at=new_ar.created_at,
                updated_at=new_ar.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 自動応答の更新
@router.put("/guilds/{guild_id}/responses/{response_id}", response_model=AutoResponseResponse)
async def update_auto_response(
    auto_response: AutoResponseUpdate,
    guild_id: str = Path(..., description="Discord Guild ID"),
    response_id: str = Path(..., description="Auto Response ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの自動応答を更新
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # 自動応答を取得
            ar = session.query(AutoResponse).filter(
                AutoResponse.id == response_id,
                AutoResponse.guild.has(discord_id=guild_id)
            ).first()
            
            if not ar:
                raise HTTPException(status_code=404, detail="Auto response not found")
            
            # 更新
            for field, value in auto_response.dict(exclude_unset=True).items():
                if hasattr(ar, field):
                    setattr(ar, field, value)
            
            # 更新日時を設定
            ar.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された自動応答を返す
            return AutoResponseResponse(
                id=ar.id,
                guild_id=guild_id,
                trigger=ar.trigger,
                response=ar.response,
                response_type=ar.response_type,
                match_type=ar.match_type,
                enabled=ar.enabled,
                cooldown=ar.cooldown,
                chance=ar.chance,
                ignore_case=ar.ignore_case,
                allowed_channels=ar.allowed_channels,
                ignored_channels=ar.ignored_channels,
                allowed_roles=ar.allowed_roles,
                ignored_roles=ar.ignored_roles,
                wildcard=ar.wildcard,
                created_at=ar.created_at,
                updated_at=ar.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 自動応答の削除
@router.delete("/guilds/{guild_id}/responses/{response_id}")
async def delete_auto_response(
    guild_id: str = Path(..., description="Discord Guild ID"),
    response_id: str = Path(..., description="Auto Response ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    指定されたサーバーの自動応答を削除
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # 自動応答を取得
            ar = session.query(AutoResponse).filter(
                AutoResponse.id == response_id,
                AutoResponse.guild.has(discord_id=guild_id)
            ).first()
            
            if not ar:
                raise HTTPException(status_code=404, detail="Auto response not found")
            
            # 削除
            session.delete(ar)
            
            # 変更をコミット
            session.commit()
            
            return {"message": "Auto response deleted successfully"}
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 自動応答の有効/無効切り替え
@router.patch("/guilds/{guild_id}/responses/{response_id}/toggle", response_model=AutoResponseResponse)
async def toggle_auto_response(
    guild_id: str = Path(..., description="Discord Guild ID"),
    response_id: str = Path(..., description="Auto Response ID"),
    current_user: dict = Depends(get_current_user),
    enabled: bool = Query(..., description="Enable or disable the auto response")
):
    """
    指定されたサーバーの自動応答の有効/無効を切り替え
    """
    # ギルドへのアクセス権を確認（モデレーター権限が必要）
    await verify_guild_access(current_user, guild_id, mod_required=True)
    
    try:
        with get_db_session() as session:
            # 自動応答を取得
            ar = session.query(AutoResponse).filter(
                AutoResponse.id == response_id,
                AutoResponse.guild.has(discord_id=guild_id)
            ).first()
            
            if not ar:
                raise HTTPException(status_code=404, detail="Auto response not found")
            
            # 有効/無効を切り替え
            ar.enabled = enabled
            
            # 更新日時を設定
            ar.updated_at = datetime.utcnow()
            
            # 変更をコミット
            session.commit()
            
            # 更新された自動応答を返す
            return AutoResponseResponse(
                id=ar.id,
                guild_id=guild_id,
                trigger=ar.trigger,
                response=ar.response,
                response_type=ar.response_type,
                match_type=ar.match_type,
                enabled=ar.enabled,
                cooldown=ar.cooldown,
                chance=ar.chance,
                ignore_case=ar.ignore_case,
                allowed_channels=ar.allowed_channels,
                ignored_channels=ar.ignored_channels,
                allowed_roles=ar.allowed_roles,
                ignored_roles=ar.ignored_roles,
                wildcard=ar.wildcard,
                created_at=ar.created_at,
                updated_at=ar.updated_at
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"自動応答切り替えエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 