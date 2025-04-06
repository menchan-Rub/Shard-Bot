import logging
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from .models import (
    Guild, GuildSettings, RaidSettings, SpamSettings,
    AIModSettings, AutoResponseSettings
)
from sqlalchemy.exc import SQLAlchemyError
import json

logger = logging.getLogger('db.repository')

class BaseRepository:
    """リポジトリの基底クラス"""
    
    def __init__(self, session: Session):
        self.session = session

class GuildRepository(BaseRepository):
    """ギルド関連のリポジトリ"""
    
    def get_guild_by_id(self, guild_id: str) -> Optional[Guild]:
        """ギルドIDからギルド情報を取得"""
        try:
            return self.session.query(Guild).filter(Guild.guild_id == guild_id).first()
        except SQLAlchemyError as e:
            logger.error(f"ギルド取得中にエラーが発生: {e}")
            return None
    
    def create_guild(self, guild_data: Dict[str, Any]) -> Optional[Guild]:
        """ギルド情報を作成"""
        try:
            guild = Guild(
                guild_id=guild_data.get('guild_id'),
                name=guild_data.get('name'),
                icon_url=guild_data.get('icon_url'),
                owner_id=guild_data.get('owner_id'),
                member_count=guild_data.get('member_count', 0)
            )
            self.session.add(guild)
            self.session.commit()
            return guild
        except SQLAlchemyError as e:
            logger.error(f"ギルド作成中にエラーが発生: {e}")
            self.session.rollback()
            return None
    
    def update_guild(self, guild_id: str, guild_data: Dict[str, Any]) -> bool:
        """ギルド情報を更新"""
        try:
            guild = self.get_guild_by_id(guild_id)
            if not guild:
                return False
            
            # 各フィールドを更新
            for key, value in guild_data.items():
                if hasattr(guild, key):
                    setattr(guild, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"ギルド更新中にエラーが発生: {e}")
            self.session.rollback()
            return False
    
    def get_or_create_guild(self, guild_id: str, guild_data: Dict[str, Any]) -> Optional[Guild]:
        """ギルド情報を取得、なければ作成"""
        guild = self.get_guild_by_id(guild_id)
        if guild:
            return guild
        
        return self.create_guild(guild_data)

class SettingsRepository(BaseRepository):
    """設定関連のリポジトリ基底クラス"""
    
    def get_guild_object(self, guild_id: str) -> Optional[Guild]:
        """ギルドオブジェクトを取得"""
        return self.session.query(Guild).filter(Guild.guild_id == guild_id).first()

class GuildSettingsRepository(SettingsRepository):
    """ギルド基本設定のリポジトリ"""
    
    def get_settings(self, guild_id: str) -> Optional[GuildSettings]:
        """ギルドの基本設定を取得"""
        guild = self.get_guild_object(guild_id)
        if not guild:
            return None
        
        return guild.settings
    
    def update_settings(self, guild_id: str, settings_data: Dict[str, Any]) -> bool:
        """ギルドの基本設定を更新"""
        try:
            guild = self.get_guild_object(guild_id)
            if not guild:
                return False
            
            # 設定がなければ作成
            if not guild.settings:
                settings = GuildSettings(guild_id=guild.id)
                self.session.add(settings)
                guild.settings = settings
            
            # 各フィールドを更新
            for key, value in settings_data.items():
                if hasattr(guild.settings, key):
                    setattr(guild.settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"ギルド設定更新中にエラーが発生: {e}")
            self.session.rollback()
            return False

class RaidSettingsRepository(SettingsRepository):
    """レイド対策設定のリポジトリ"""
    
    def get_settings(self, guild_id: str) -> Optional[RaidSettings]:
        """ギルドのレイド対策設定を取得"""
        guild = self.get_guild_object(guild_id)
        if not guild:
            return None
        
        return guild.raid_settings
    
    def update_settings(self, guild_id: str, settings_data: Dict[str, Any]) -> bool:
        """ギルドのレイド対策設定を更新"""
        try:
            guild = self.get_guild_object(guild_id)
            if not guild:
                return False
            
            # 設定がなければ作成
            if not guild.raid_settings:
                settings = RaidSettings(guild_id=guild.id)
                self.session.add(settings)
                guild.raid_settings = settings
            
            # 各フィールドを更新
            for key, value in settings_data.items():
                if hasattr(guild.raid_settings, key):
                    setattr(guild.raid_settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"レイド対策設定更新中にエラーが発生: {e}")
            self.session.rollback()
            return False

class SpamSettingsRepository(SettingsRepository):
    """スパム対策設定のリポジトリ"""
    
    def get_settings(self, guild_id: str) -> Optional[SpamSettings]:
        """ギルドのスパム対策設定を取得"""
        guild = self.get_guild_object(guild_id)
        if not guild:
            return None
        
        return guild.spam_settings
    
    def update_settings(self, guild_id: str, settings_data: Dict[str, Any]) -> bool:
        """ギルドのスパム対策設定を更新"""
        try:
            guild = self.get_guild_object(guild_id)
            if not guild:
                return False
            
            # 設定がなければ作成
            if not guild.spam_settings:
                settings = SpamSettings(guild_id=guild.id)
                self.session.add(settings)
                guild.spam_settings = settings
            
            # 各フィールドを更新
            for key, value in settings_data.items():
                if hasattr(guild.spam_settings, key):
                    setattr(guild.spam_settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"スパム対策設定更新中にエラーが発生: {e}")
            self.session.rollback()
            return False

class AIModSettingsRepository(SettingsRepository):
    """AIモデレーション設定のリポジトリ"""
    
    def get_settings(self, guild_id: str) -> Optional[AIModSettings]:
        """ギルドのAIモデレーション設定を取得"""
        guild = self.get_guild_object(guild_id)
        if not guild:
            return None
        
        return guild.ai_mod_settings
    
    def update_settings(self, guild_id: str, settings_data: Dict[str, Any]) -> bool:
        """ギルドのAIモデレーション設定を更新"""
        try:
            guild = self.get_guild_object(guild_id)
            if not guild:
                return False
            
            # 設定がなければ作成
            if not guild.ai_mod_settings:
                settings = AIModSettings(guild_id=guild.id)
                self.session.add(settings)
                guild.ai_mod_settings = settings
            
            # 各フィールドを更新
            for key, value in settings_data.items():
                if hasattr(guild.ai_mod_settings, key):
                    setattr(guild.ai_mod_settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"AIモデレーション設定更新中にエラーが発生: {e}")
            self.session.rollback()
            return False

class AutoResponseSettingsRepository(SettingsRepository):
    """自動応答設定のリポジトリ"""
    
    def get_settings(self, guild_id: str) -> Optional[AutoResponseSettings]:
        """ギルドの自動応答設定を取得"""
        guild = self.get_guild_object(guild_id)
        if not guild:
            return None
        
        return guild.auto_response_settings
    
    def update_settings(self, guild_id: str, settings_data: Dict[str, Any]) -> bool:
        """ギルドの自動応答設定を更新"""
        try:
            guild = self.get_guild_object(guild_id)
            if not guild:
                return False
            
            # 設定がなければ作成
            if not guild.auto_response_settings:
                settings = AutoResponseSettings(guild_id=guild.id)
                self.session.add(settings)
                guild.auto_response_settings = settings
            
            # カスタム応答を特別に処理
            if 'custom_responses' in settings_data and isinstance(settings_data['custom_responses'], dict):
                guild.auto_response_settings.custom_responses = settings_data.pop('custom_responses')
            
            # 各フィールドを更新
            for key, value in settings_data.items():
                if hasattr(guild.auto_response_settings, key):
                    setattr(guild.auto_response_settings, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"自動応答設定更新中にエラーが発生: {e}")
            self.session.rollback()
            return False 