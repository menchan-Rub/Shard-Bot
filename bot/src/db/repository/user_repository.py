from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

from bot.src.db.models import User
from .base_repository import BaseRepository

logger = logging.getLogger('bot.repository.user')

class UserRepository(BaseRepository[User]):
    """ユーザー情報に関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, User)
    
    def get_user_by_discord_id(self, discord_id: str) -> Optional[User]:
        """
        Discord IDによるユーザーの取得
        
        Args:
            discord_id (str): DiscordのユーザーID
            
        Returns:
            Optional[User]: 見つかったユーザー、なければNone
        """
        try:
            return self.session.query(User).filter(User.user_id == discord_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Discord IDによるユーザー取得中にエラー: {e}")
            return None
    
    def create_user(self, data: Dict[str, Any]) -> Optional[User]:
        """
        ユーザーの新規作成
        
        Args:
            data (Dict[str, Any]): ユーザー作成データ
            
        Returns:
            Optional[User]: 作成されたユーザー、失敗時はNone
        """
        try:
            # Discord IDが存在するかチェック
            if 'user_id' not in data or not data['user_id']:
                logger.error("ユーザー作成にDiscord IDが必要です")
                return None
                
            # 既存のユーザーをチェック
            existing = self.get_user_by_discord_id(data['user_id'])
            if existing:
                logger.info(f"ユーザーID {data['user_id']} は既に存在します")
                return existing
                
            # 必須フィールドの確認
            if 'username' not in data or not data['username']:
                data['username'] = f"User-{data['user_id']}"
            
            # 作成日時を設定
            data['created_at'] = datetime.utcnow()
            data['updated_at'] = datetime.utcnow()
            
            # ユーザー作成
            user = User(**data)
            self.session.add(user)
            self.session.commit()
            return user
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ユーザー作成中にエラー: {e}")
            return None
    
    def update_user(self, discord_id: str, data: Dict[str, Any]) -> bool:
        """
        ユーザー情報の更新
        
        Args:
            discord_id (str): 更新対象のDiscordユーザーID
            data (Dict[str, Any]): 更新データ
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            user = self.get_user_by_discord_id(discord_id)
            if not user:
                logger.warning(f"更新対象のユーザー {discord_id} が見つかりません")
                return False
            
            # 更新可能なフィールドを制限
            allowed_fields = [
                'username', 'email', 'avatar_url', 'is_admin', 
                'is_active', 'last_login'
            ]
            
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            update_data['updated_at'] = datetime.utcnow()
            
            for key, value in update_data.items():
                setattr(user, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ユーザー更新中にエラー: {e}")
            return False
    
    def delete_user(self, discord_id: str) -> bool:
        """
        ユーザーの削除
        
        Args:
            discord_id (str): 削除対象のDiscordユーザーID
            
        Returns:
            bool: 削除成功はTrue、失敗はFalse
        """
        try:
            user = self.get_user_by_discord_id(discord_id)
            if not user:
                logger.warning(f"削除対象のユーザー {discord_id} が見つかりません")
                return False
            
            self.session.delete(user)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"ユーザー削除中にエラー: {e}")
            return False
    
    def set_last_login(self, discord_id: str) -> bool:
        """
        最終ログイン時間を更新
        
        Args:
            discord_id (str): DiscordユーザーID
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            user = self.get_user_by_discord_id(discord_id)
            if not user:
                logger.warning(f"ユーザー {discord_id} が見つかりません")
                return False
            
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"最終ログイン時間更新中にエラー: {e}")
            return False
    
    def get_admins(self) -> List[User]:
        """
        管理者ユーザーのリストを取得
        
        Returns:
            List[User]: 管理者ユーザーのリスト
        """
        try:
            return self.session.query(User).filter(User.is_admin == True).all()
        except SQLAlchemyError as e:
            logger.error(f"管理者リスト取得中にエラー: {e}")
            return [] 