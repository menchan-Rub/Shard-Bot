"""
違反管理モジュール
ユーザー違反（警告、ミュート、キック、バン）の管理を行います
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc

from bot.src.db.database import get_db_session
from bot.src.db.models import UserInfraction, ModerationAction, Guild

logger = logging.getLogger(__name__)

class InfractionManager:
    """
    ユーザー違反を管理するクラス
    """
    
    def __init__(self, bot):
        """
        初期化
        
        Args:
            bot: Botインスタンス (APIからの呼び出し時にはNoneでも可)
        """
        self.bot = bot
        self.logger = logging.getLogger("bot.infractions")
    
    async def get_user_infractions(self, guild_id: str, user_id: str, 
                                   active_only: bool = False) -> List[Dict[str, Any]]:
        """
        ユーザーの違反履歴を取得
        
        Args:
            guild_id: サーバーID
            user_id: ユーザーID
            active_only: アクティブな違反のみ取得するかどうか
            
        Returns:
            違反履歴のリスト
        """
        try:
            with get_db_session() as session:
                query = session.query(UserInfraction).filter(
                    UserInfraction.guild.has(discord_id=guild_id),
                    UserInfraction.user_id == user_id
                )
                
                if active_only:
                    query = query.filter(UserInfraction.active == True)
                
                infractions = query.order_by(UserInfraction.created_at.desc()).all()
                
                result = []
                for infraction in infractions:
                    result.append({
                        "id": infraction.id,
                        "action_type": infraction.action_type,
                        "reason": infraction.reason,
                        "moderator_id": infraction.moderator_id,
                        "duration": infraction.duration,
                        "active": infraction.active,
                        "created_at": infraction.created_at,
                        "expires_at": infraction.expires_at
                    })
                
                return result
                
        except SQLAlchemyError as e:
            self.logger.error(f"違反履歴取得エラー: {e}")
            return []
    
    async def warn_user(self, guild_id: str, moderator_id: str, user_id: str, 
                       reason: Optional[str] = None) -> Optional[int]:
        """
        ユーザーに警告を与える
        
        Args:
            guild_id: サーバーID
            moderator_id: モデレーターID
            user_id: ユーザーID
            reason: 理由
            
        Returns:
            作成された違反のID、失敗した場合はNone
        """
        try:
            # モデレーションアクションとユーザー違反を作成
            with get_db_session() as session:
                # Guildを取得
                guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    self.logger.error(f"Guild not found: {guild_id}")
                    return None
                
                # 新しいアクションを作成
                action = ModerationAction(
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    target_id=user_id,
                    action_type="warn",
                    reason=reason,
                    action_metadata={}
                )
                session.add(action)
                session.flush()  # IDを生成するためにフラッシュ
                
                # 違反を作成
                infraction = UserInfraction(
                    action_id=action.id,
                    guild_id=guild.id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action_type="warn",
                    reason=reason,
                    active=True,
                    created_at=datetime.utcnow()
                )
                session.add(infraction)
                session.commit()
                
                # Botインスタンスがある場合は通知なども行う
                if self.bot:
                    asyncio.create_task(self._notify_user_warn(guild_id, user_id, reason))
                
                return infraction.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"警告作成エラー: {e}")
            return None
    
    async def mute_user(self, guild_id: str, moderator_id: str, user_id: str,
                       reason: Optional[str] = None, duration: Optional[int] = None) -> Optional[int]:
        """
        ユーザーをミュートする
        
        Args:
            guild_id: サーバーID
            moderator_id: モデレーターID
            user_id: ユーザーID
            reason: 理由
            duration: ミュート時間（分）、Noneの場合は無期限
            
        Returns:
            作成された違反のID、失敗した場合はNone
        """
        try:
            # 有効期限を計算
            expires_at = None
            if duration:
                expires_at = datetime.utcnow() + timedelta(minutes=duration)
            
            # モデレーションアクションとユーザー違反を作成
            with get_db_session() as session:
                # Guildを取得
                guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    self.logger.error(f"Guild not found: {guild_id}")
                    return None
                
                # 新しいアクションを作成
                action = ModerationAction(
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    target_id=user_id,
                    action_type="mute",
                    reason=reason,
                    action_metadata={"duration": duration}
                )
                session.add(action)
                session.flush()
                
                # 違反を作成
                infraction = UserInfraction(
                    action_id=action.id,
                    guild_id=guild.id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action_type="mute",
                    reason=reason,
                    duration=duration,
                    active=True,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at
                )
                session.add(infraction)
                session.commit()
                
                # Botインスタンスがある場合は実際のミュート処理も行う
                if self.bot:
                    asyncio.create_task(self._apply_mute(guild_id, user_id, duration, reason))
                
                return infraction.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"ミュート作成エラー: {e}")
            return None
    
    async def kick_user(self, guild_id: str, moderator_id: str, user_id: str,
                       reason: Optional[str] = None) -> Optional[int]:
        """
        ユーザーをキックする
        
        Args:
            guild_id: サーバーID
            moderator_id: モデレーターID
            user_id: ユーザーID
            reason: 理由
            
        Returns:
            作成された違反のID、失敗した場合はNone
        """
        try:
            # モデレーションアクションとユーザー違反を作成
            with get_db_session() as session:
                # Guildを取得
                guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    self.logger.error(f"Guild not found: {guild_id}")
                    return None
                
                # 新しいアクションを作成
                action = ModerationAction(
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    target_id=user_id,
                    action_type="kick",
                    reason=reason,
                    action_metadata={}
                )
                session.add(action)
                session.flush()
                
                # 違反を作成
                infraction = UserInfraction(
                    action_id=action.id,
                    guild_id=guild.id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action_type="kick",
                    reason=reason,
                    active=False,  # キックは一度きりのアクション
                    created_at=datetime.utcnow()
                )
                session.add(infraction)
                session.commit()
                
                # Botインスタンスがある場合は実際のキック処理も行う
                if self.bot:
                    asyncio.create_task(self._apply_kick(guild_id, user_id, reason))
                
                return infraction.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"キック作成エラー: {e}")
            return None
    
    async def ban_user(self, guild_id: str, moderator_id: str, user_id: str,
                      reason: Optional[str] = None, delete_message_days: int = 0) -> Optional[int]:
        """
        ユーザーをバンする
        
        Args:
            guild_id: サーバーID
            moderator_id: モデレーターID
            user_id: ユーザーID
            reason: 理由
            delete_message_days: 削除するメッセージの日数（0-7）
            
        Returns:
            作成された違反のID、失敗した場合はNone
        """
        try:
            # モデレーションアクションとユーザー違反を作成
            with get_db_session() as session:
                # Guildを取得
                guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    self.logger.error(f"Guild not found: {guild_id}")
                    return None
                
                # 新しいアクションを作成
                action = ModerationAction(
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    target_id=user_id,
                    action_type="ban",
                    reason=reason,
                    action_metadata={"delete_message_days": delete_message_days}
                )
                session.add(action)
                session.flush()
                
                # 違反を作成
                infraction = UserInfraction(
                    action_id=action.id,
                    guild_id=guild.id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action_type="ban",
                    reason=reason,
                    active=True,  # バンは継続的なアクション
                    created_at=datetime.utcnow()
                )
                session.add(infraction)
                session.commit()
                
                # Botインスタンスがある場合は実際のバン処理も行う
                if self.bot:
                    asyncio.create_task(self._apply_ban(guild_id, user_id, reason, delete_message_days))
                
                return infraction.id
                
        except SQLAlchemyError as e:
            self.logger.error(f"バン作成エラー: {e}")
            return None
    
    async def unban_user(self, guild_id: str, moderator_id: str, user_id: str,
                        reason: Optional[str] = None) -> bool:
        """
        ユーザーのバンを解除する
        
        Args:
            guild_id: サーバーID
            moderator_id: モデレーターID
            user_id: ユーザーID
            reason: 理由
            
        Returns:
            成功したかどうか
        """
        try:
            # 既存のアクティブなバン違反を非アクティブにする
            with get_db_session() as session:
                # Guildを取得
                guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    self.logger.error(f"Guild not found: {guild_id}")
                    return False
                
                # アクティブなバン違反を取得
                infractions = session.query(UserInfraction).filter(
                    UserInfraction.guild_id == guild.id,
                    UserInfraction.user_id == user_id,
                    UserInfraction.action_type == "ban",
                    UserInfraction.active == True
                ).all()
                
                # 違反を非アクティブにする
                for infraction in infractions:
                    infraction.active = False
                
                # 新しいアクションを作成（バン解除）
                action = ModerationAction(
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    target_id=user_id,
                    action_type="unban",
                    reason=reason,
                    action_metadata={}
                )
                session.add(action)
                session.commit()
                
                # Botインスタンスがある場合は実際のバン解除処理も行う
                if self.bot:
                    asyncio.create_task(self._apply_unban(guild_id, user_id, reason))
                
                return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"バン解除エラー: {e}")
            return False
    
    # 以下はBotインスタンスを使った実際のアクション適用メソッド
    # APIからの呼び出し時にはBotインスタンスがないため実行されない
    
    async def _notify_user_warn(self, guild_id: str, user_id: str, reason: Optional[str]) -> None:
        """ユーザーに警告を通知する（実装省略）"""
        # 実装は省略（Botインスタンスを使ってDMを送信するなど）
        pass
    
    async def _apply_mute(self, guild_id: str, user_id: str, duration: Optional[int], reason: Optional[str]) -> None:
        """ユーザーをミュートする（実装省略）"""
        # 実装は省略（Botインスタンスを使ってタイムアウトを設定するなど）
        pass
    
    async def _apply_kick(self, guild_id: str, user_id: str, reason: Optional[str]) -> None:
        """ユーザーをキックする（実装省略）"""
        # 実装は省略（Botインスタンスを使ってキックするなど）
        pass
    
    async def _apply_ban(self, guild_id: str, user_id: str, reason: Optional[str], delete_message_days: int) -> None:
        """ユーザーをバンする（実装省略）"""
        # 実装は省略（Botインスタンスを使ってバンするなど）
        pass
    
    async def _apply_unban(self, guild_id: str, user_id: str, reason: Optional[str]) -> None:
        """ユーザーのバンを解除する（実装省略）"""
        # 実装は省略（Botインスタンスを使ってバン解除するなど）
        pass 