from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from bot.src.db.models import Guild
from .base_repository import BaseRepository

logger = logging.getLogger('bot.repository.guild')

class GuildRepository(BaseRepository[Guild]):
    """ギルド情報に関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, Guild)
    
    def get_guild_by_id(self, discord_id: str) -> Optional[Guild]:
        """
        Discord IDによるギルドの取得
        
        Args:
            discord_id (str): DiscordのギルドID
            
        Returns:
            Optional[Guild]: 見つかったギルド、なければNone
        """
        try:
            return self.session.query(Guild).filter(Guild.discord_id == discord_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Discord IDによるギルド取得中にエラー: {e}")
            return None
    
    def create_guild(self, data: Dict[str, Any]) -> Optional[Guild]:
        """
        ギルドの新規作成
        
        Args:
            data (Dict[str, Any]): ギルド作成データ
            
        Returns:
            Optional[Guild]: 作成されたギルド、失敗時はNone
        """
        try:
            # Discord IDが存在するかチェック
            if 'discord_id' not in data or not data['discord_id']:
                logger.error("ギルド作成にDiscord IDが必要です")
                return None
                
            # 既存のギルドをチェック
            existing = self.get_guild_by_id(data['discord_id'])
            if existing:
                logger.info(f"ギルドID {data['discord_id']} は既に存在します")
                return existing
                
            # 必須フィールドの確認
            required_fields = ['name', 'owner_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    # ownerとnameは必須
                    # name未設定の場合、guild_idから生成
                    if field == 'name' and 'discord_id' in data:
                        data['name'] = f"Guild-{data['discord_id']}"
                    else:
                        # デフォルトのオーナーID
                        data['owner_id'] = "0"
            
            # ギルド作成
            guild = Guild(**data)
            self.session.add(guild)
            self.session.commit()
            return guild
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ギルド作成中にエラー: {e}")
            return None
    
    def update_guild(self, discord_id: str, data: Dict[str, Any]) -> bool:
        """
        ギルド情報の更新
        
        Args:
            discord_id (str): 更新対象のDiscordギルドID
            data (Dict[str, Any]): 更新データ
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            guild = self.get_guild_by_id(discord_id)
            if not guild:
                logger.warning(f"更新対象のギルド {discord_id} が見つかりません")
                return False
            
            # 更新可能なフィールドを制限
            allowed_fields = [
                'name', 'icon', 'member_count', 'owner_id',
                'premium_tier', 'updated_at'
            ]
            
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            
            for key, value in update_data.items():
                setattr(guild, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ギルド更新中にエラー: {e}")
            return False
    
    def delete_guild(self, discord_id: str) -> bool:
        """
        ギルドの削除
        
        Args:
            discord_id (str): 削除対象のDiscordギルドID
            
        Returns:
            bool: 削除成功はTrue、失敗はFalse
        """
        try:
            guild = self.get_guild_by_id(discord_id)
            if not guild:
                logger.warning(f"削除対象のギルド {discord_id} が見つかりません")
                return False
            
            self.session.delete(guild)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ギルド削除中にエラー: {e}")
            return False
    
    def get_guilds_by_owner(self, owner_id: str) -> List[Guild]:
        """
        オーナーIDによるギルド検索
        
        Args:
            owner_id (str): オーナーのDiscord ID
            
        Returns:
            List[Guild]: ギルドのリスト
        """
        try:
            return self.session.query(Guild).filter(Guild.owner_id == owner_id).all()
        except SQLAlchemyError as e:
            logger.error(f"オーナーIDによるギルド検索中にエラー: {e}")
            return [] 