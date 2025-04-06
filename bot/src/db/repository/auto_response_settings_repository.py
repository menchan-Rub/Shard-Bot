from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import json

from bot.src.db.models import AutoResponseSettings, Guild
from .base_repository import BaseRepository
from .guild_repository import GuildRepository

logger = logging.getLogger('bot.repository.auto_response_settings')

class AutoResponseSettingsRepository(BaseRepository[AutoResponseSettings]):
    """自動応答設定に関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, AutoResponseSettings)
        self.guild_repo = GuildRepository(session)
    
    def get_settings(self, guild_id: str) -> Optional[AutoResponseSettings]:
        """
        ギルドIDによる自動応答設定の取得
        
        Args:
            guild_id (str): DiscordのギルドID
            
        Returns:
            Optional[AutoResponseSettings]: 見つかった設定、なければNone
        """
        try:
            # ギルドの内部IDを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が存在しません")
                return None
            
            # 設定を取得
            return self.session.query(AutoResponseSettings).filter(AutoResponseSettings.guild_id == guild.id).first()
        except SQLAlchemyError as e:
            logger.error(f"自動応答設定の取得中にエラー: {e}")
            return None
    
    def create_settings(self, guild_id: str, data: Dict[str, Any] = None) -> Optional[AutoResponseSettings]:
        """
        自動応答設定の新規作成
        
        Args:
            guild_id (str): DiscordのギルドID
            data (Dict[str, Any], optional): 設定データ、デフォルトはNone
            
        Returns:
            Optional[AutoResponseSettings]: 作成された設定、失敗時はNone
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
            existing = self.session.query(AutoResponseSettings).filter(AutoResponseSettings.guild_id == guild.id).first()
            if existing:
                logger.info(f"ギルド {guild_id} の自動応答設定は既に存在します")
                return existing
            
            # 設定を作成
            settings_data = data or {}
            settings_data['guild_id'] = guild.id
            
            # JSON型フィールドを確認
            if 'custom_responses' in settings_data and not isinstance(settings_data['custom_responses'], dict):
                try:
                    settings_data['custom_responses'] = json.loads(settings_data['custom_responses'])
                except (json.JSONDecodeError, TypeError):
                    settings_data['custom_responses'] = {}
            
            settings = AutoResponseSettings(**settings_data)
            self.session.add(settings)
            self.session.commit()
            return settings
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"自動応答設定の作成中にエラー: {e}")
            return None
    
    def update_settings(self, guild_id: str, data: Dict[str, Any]) -> bool:
        """
        自動応答設定の更新
        
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
            
            # JSON型フィールドを確認
            if 'custom_responses' in data and not isinstance(data['custom_responses'], dict):
                try:
                    data['custom_responses'] = json.loads(data['custom_responses'])
                except (json.JSONDecodeError, TypeError):
                    data['custom_responses'] = {}
            
            # 設定を更新
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"自動応答設定の更新中にエラー: {e}")
            return False
    
    def delete_settings(self, guild_id: str) -> bool:
        """
        自動応答設定の削除
        
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
            settings = self.session.query(AutoResponseSettings).filter(AutoResponseSettings.guild_id == guild.id).first()
            if not settings:
                logger.warning(f"ギルド {guild_id} の自動応答設定が存在しません")
                return False
            
            self.session.delete(settings)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"自動応答設定の削除中にエラー: {e}")
            return False
    
    def add_custom_response(self, guild_id: str, trigger: str, responses: List[str]) -> bool:
        """
        カスタム応答パターンを追加
        
        Args:
            guild_id (str): DiscordのギルドID
            trigger (str): トリガーテキスト
            responses (List[str]): 応答テキストのリスト
            
        Returns:
            bool: 追加成功はTrue、失敗はFalse
        """
        try:
            settings = self.get_settings(guild_id)
            if not settings:
                # 設定がない場合は新規作成
                data = {'custom_responses': {trigger: responses}}
                return self.create_settings(guild_id, data) is not None
            
            # 既存のカスタム応答を取得
            custom_responses = settings.custom_responses or {}
            
            # 応答を追加/更新
            custom_responses[trigger] = responses
            
            # 設定を更新
            settings.custom_responses = custom_responses
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"カスタム応答追加中にエラー: {e}")
            return False
    
    def remove_custom_response(self, guild_id: str, trigger: str) -> bool:
        """
        カスタム応答パターンを削除
        
        Args:
            guild_id (str): DiscordのギルドID
            trigger (str): 削除するトリガーテキスト
            
        Returns:
            bool: 削除成功はTrue、失敗はFalse
        """
        try:
            settings = self.get_settings(guild_id)
            if not settings or not settings.custom_responses:
                logger.warning(f"ギルド {guild_id} にカスタム応答がありません")
                return False
            
            # 既存のカスタム応答を取得
            custom_responses = settings.custom_responses
            
            # トリガーが存在するか確認
            if trigger not in custom_responses:
                logger.warning(f"ギルド {guild_id} にトリガー '{trigger}' のカスタム応答がありません")
                return False
            
            # トリガーを削除
            del custom_responses[trigger]
            
            # 設定を更新
            settings.custom_responses = custom_responses
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"カスタム応答削除中にエラー: {e}")
            return False
    
    def get_all_custom_responses(self, guild_id: str) -> Dict[str, List[str]]:
        """
        全てのカスタム応答パターンを取得
        
        Args:
            guild_id (str): DiscordのギルドID
            
        Returns:
            Dict[str, List[str]]: キーがトリガー、値が応答リストの辞書
        """
        try:
            settings = self.get_settings(guild_id)
            if not settings:
                return {}
            
            return settings.custom_responses or {}
        except SQLAlchemyError as e:
            logger.error(f"カスタム応答取得中にエラー: {e}")
            return {} 