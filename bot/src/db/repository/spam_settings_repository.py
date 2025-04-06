from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from bot.src.db.models import SpamSettings, Guild
from .base_repository import BaseRepository
from .guild_repository import GuildRepository

logger = logging.getLogger('bot.repository.spam_settings')

class SpamSettingsRepository(BaseRepository[SpamSettings]):
    """スパム保護設定に関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, SpamSettings)
        self.guild_repo = GuildRepository(session)
    
    def get_settings(self, guild_id: str) -> Optional[SpamSettings]:
        """
        ギルドIDによるスパム設定の取得
        
        Args:
            guild_id (str): DiscordのギルドID
            
        Returns:
            Optional[SpamSettings]: 見つかった設定、なければNone
        """
        try:
            # ギルドの内部IDを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が存在しません")
                return None
            
            # 設定を取得
            return self.session.query(SpamSettings).filter(SpamSettings.guild_id == guild.id).first()
        except SQLAlchemyError as e:
            logger.error(f"スパム設定の取得中にエラー: {e}")
            return None
    
    def create_settings(self, guild_id: str, data: Dict[str, Any] = None) -> Optional[SpamSettings]:
        """
        スパム設定の新規作成
        
        Args:
            guild_id (str): DiscordのギルドID
            data (Dict[str, Any], optional): 設定データ、デフォルトはNone
            
        Returns:
            Optional[SpamSettings]: 作成された設定、失敗時はNone
        """
        try:
            # ギルドの内部IDを取得、ない場合は作成
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                guild_data = {
                    "discord_id": guild_id,
                    "name": f"Guild-{guild_id}",
                    "owner_id": "0"
                }
                guild = self.guild_repo.create_guild(guild_data)
                if not guild:
                    logger.error(f"ギルド {guild_id} の作成に失敗しました")
                    return None
            
            # 既存の設定をチェック
            existing = self.session.query(SpamSettings).filter(SpamSettings.guild_id == guild.id).first()
            if existing:
                logger.info(f"ギルド {guild_id} のスパム設定は既に存在します")
                return existing
            
            # 設定を作成
            settings_data = data or {}
            settings_data['guild_id'] = guild.id
            
            settings = SpamSettings(**settings_data)
            self.session.add(settings)
            self.session.commit()
            return settings
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"スパム設定の作成中にエラー: {e}")
            return None
    
    def update_settings(self, guild_id: str, data: Dict[str, Any]) -> bool:
        """
        スパム設定の更新
        
        Args:
            guild_id (str): DiscordのギルドID
            data (Dict[str, Any]): 更新データ
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            # 既存の設定を取得
            settings = self.get_settings(guild_id)
            
            # 設定がない場合は作成
            if not settings:
                created = self.create_settings(guild_id, data)
                return created is not None
            
            # 設定を更新
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"スパム設定の更新中にエラー: {e}")
            return False
    
    def delete_settings(self, guild_id: str) -> bool:
        """
        スパム設定の削除
        
        Args:
            guild_id (str): DiscordのギルドID
            
        Returns:
            bool: 削除成功はTrue、失敗はFalse
        """
        try:
            # ギルドの内部IDを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が存在しません")
                return False
            
            # 設定を取得して削除
            settings = self.session.query(SpamSettings).filter(SpamSettings.guild_id == guild.id).first()
            if not settings:
                logger.warning(f"ギルド {guild_id} のスパム設定が存在しません")
                return False
            
            self.session.delete(settings)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"スパム設定の削除中にエラー: {e}")
            return False
            
    def update_spam_limits(self, guild_id: str, limits: Dict[str, int]) -> bool:
        """
        スパム制限値を更新
        
        Args:
            guild_id (str): DiscordのギルドID
            limits (Dict[str, int]): 更新する制限値
                {
                    'message_rate_limit': 5,
                    'message_time_window': 3,
                    ...
                }
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            settings = self.get_settings(guild_id)
            if not settings:
                # 設定がない場合は新規作成
                return self.create_settings(guild_id, limits) is not None
            
            # 更新可能なフィールドを制限
            allowed_fields = [
                'message_rate_limit', 'message_time_window', 
                'mention_limit', 'role_mention_limit',
                'duplicate_limit', 'url_limit'
            ]
            
            update_data = {k: v for k, v in limits.items() if k in allowed_fields}
            
            # 設定を更新
            for key, value in update_data.items():
                setattr(settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"スパム制限値の更新中にエラー: {e}")
            return False 