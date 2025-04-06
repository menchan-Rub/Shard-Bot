from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from bot.src.db.models import AIModSettings, Guild
from .base_repository import BaseRepository
from .guild_repository import GuildRepository

logger = logging.getLogger('bot.repository.ai_mod_settings')

class AIModSettingsRepository(BaseRepository[AIModSettings]):
    """AIモデレーション設定に関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, AIModSettings)
        self.guild_repo = GuildRepository(session)
    
    def get_settings(self, guild_id: str) -> Optional[AIModSettings]:
        """
        ギルドIDによるAIモデレーション設定の取得
        
        Args:
            guild_id (str): DiscordのギルドID
            
        Returns:
            Optional[AIModSettings]: 見つかった設定、なければNone
        """
        try:
            # ギルドの内部IDを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が存在しません")
                return None
            
            # 設定を取得
            return self.session.query(AIModSettings).filter(AIModSettings.guild_id == guild.id).first()
        except SQLAlchemyError as e:
            logger.error(f"AIモデレーション設定の取得中にエラー: {e}")
            return None
    
    def create_settings(self, guild_id: str, data: Dict[str, Any] = None) -> Optional[AIModSettings]:
        """
        AIモデレーション設定の新規作成
        
        Args:
            guild_id (str): DiscordのギルドID
            data (Dict[str, Any], optional): 設定データ、デフォルトはNone
            
        Returns:
            Optional[AIModSettings]: 作成された設定、失敗時はNone
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
            existing = self.session.query(AIModSettings).filter(AIModSettings.guild_id == guild.id).first()
            if existing:
                logger.info(f"ギルド {guild_id} のAIモデレーション設定は既に存在します")
                return existing
            
            # 設定を作成
            settings_data = data or {}
            settings_data['guild_id'] = guild.id
            
            settings = AIModSettings(**settings_data)
            self.session.add(settings)
            self.session.commit()
            return settings
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"AIモデレーション設定の作成中にエラー: {e}")
            return None
    
    def update_settings(self, guild_id: str, data: Dict[str, Any]) -> bool:
        """
        AIモデレーション設定の更新
        
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
            logger.error(f"AIモデレーション設定の更新中にエラー: {e}")
            return False
    
    def delete_settings(self, guild_id: str) -> bool:
        """
        AIモデレーション設定の削除
        
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
            settings = self.session.query(AIModSettings).filter(AIModSettings.guild_id == guild.id).first()
            if not settings:
                logger.warning(f"ギルド {guild_id} のAIモデレーション設定が存在しません")
                return False
            
            self.session.delete(settings)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"AIモデレーション設定の削除中にエラー: {e}")
            return False
            
    def update_thresholds(self, guild_id: str, thresholds: Dict[str, float]) -> bool:
        """
        AIモデレーションの閾値を更新
        
        Args:
            guild_id (str): DiscordのギルドID
            thresholds (Dict[str, float]): 更新する閾値データ
                {
                    'toxicity_threshold': 0.8,
                    'identity_attack_threshold': 0.8,
                    ...
                }
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            settings = self.get_settings(guild_id)
            if not settings:
                # 設定がない場合は新規作成
                return self.create_settings(guild_id, thresholds) is not None
            
            # 更新可能なフィールドを制限
            allowed_fields = [
                'toxicity_threshold', 'identity_attack_threshold',
                'insult_threshold', 'threat_threshold', 'sexual_threshold'
            ]
            
            update_data = {k: v for k, v in thresholds.items() if k in allowed_fields}
            
            # 設定を更新
            for key, value in update_data.items():
                setattr(settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"AIモデレーション閾値の更新中にエラー: {e}")
            return False 