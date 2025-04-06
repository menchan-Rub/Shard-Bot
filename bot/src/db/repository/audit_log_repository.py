from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta

from bot.src.db.models import AuditLog, Guild, User
from .base_repository import BaseRepository
from .guild_repository import GuildRepository
from .user_repository import UserRepository

logger = logging.getLogger('bot.repository.audit_log')

class AuditLogRepository(BaseRepository[AuditLog]):
    """監査ログに関するリポジトリ"""
    
    def __init__(self, session: Session):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
        """
        super().__init__(session, AuditLog)
        self.guild_repo = GuildRepository(session)
        self.user_repo = UserRepository(session)
    
    def add_log(self, guild_id: str, user_id: str, action: str, 
                target_id: Optional[str] = None, target_type: Optional[str] = None, 
                details: Optional[Dict[str, Any]] = None) -> Optional[AuditLog]:
        """
        監査ログの追加
        
        Args:
            guild_id (str): DiscordのギルドID
            user_id (str): 実行したユーザーのDiscord ID
            action (str): 実行されたアクション
            target_id (str, optional): 対象のID
            target_type (str, optional): 対象の種類
            details (Dict[str, Any], optional): 詳細情報
            
        Returns:
            Optional[AuditLog]: 作成された監査ログ、失敗時はNone
        """
        try:
            # ギルドの取得または作成
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
            
            # ユーザーの取得または作成
            user = self.user_repo.get_user_by_discord_id(user_id)
            if not user:
                user_data = {
                    "user_id": user_id,
                    "username": f"User-{user_id}"
                }
                user = self.user_repo.create_user(user_data)
                if not user:
                    logger.error(f"ユーザー {user_id} の作成に失敗しました")
                    return None
            
            # 監査ログの作成
            log_data = {
                "guild_id": guild.id,
                "user_id": user.id,
                "action": action,
                "target_id": target_id,
                "target_type": target_type,
                "details": details or {},
                "created_at": datetime.utcnow()
            }
            
            log = AuditLog(**log_data)
            self.session.add(log)
            self.session.commit()
            return log
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"監査ログ追加中にエラー: {e}")
            return None
    
    def get_logs_by_guild(self, guild_id: str, limit: int = 100, 
                        action_type: Optional[str] = None, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[AuditLog]:
        """
        ギルドの監査ログを取得
        
        Args:
            guild_id (str): DiscordのギルドID
            limit (int, optional): 取得する最大数
            action_type (str, optional): フィルタするアクションタイプ
            start_date (datetime, optional): 開始日時
            end_date (datetime, optional): 終了日時
            
        Returns:
            List[AuditLog]: 監査ログのリスト
        """
        try:
            # ギルドを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が見つかりません")
                return []
            
            # クエリの構築
            query = self.session.query(AuditLog).filter(AuditLog.guild_id == guild.id)
            
            if action_type:
                query = query.filter(AuditLog.action == action_type)
            
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
                
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)
            
            # 結果を取得（降順）
            return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"ギルド監査ログ取得中にエラー: {e}")
            return []
    
    def get_logs_by_user(self, user_id: str, limit: int = 100,
                        guild_id: Optional[str] = None) -> List[AuditLog]:
        """
        ユーザーの監査ログを取得
        
        Args:
            user_id (str): DiscordのユーザーID
            limit (int, optional): 取得する最大数
            guild_id (str, optional): 特定のギルドでフィルタ
            
        Returns:
            List[AuditLog]: 監査ログのリスト
        """
        try:
            # ユーザーを取得
            user = self.user_repo.get_user_by_discord_id(user_id)
            if not user:
                logger.warning(f"ユーザー {user_id} が見つかりません")
                return []
            
            # クエリの構築
            query = self.session.query(AuditLog).filter(AuditLog.user_id == user.id)
            
            if guild_id:
                guild = self.guild_repo.get_guild_by_id(guild_id)
                if guild:
                    query = query.filter(AuditLog.guild_id == guild.id)
            
            # 結果を取得（降順）
            return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"ユーザー監査ログ取得中にエラー: {e}")
            return []
    
    def get_logs_by_action(self, action: str, limit: int = 100,
                          guild_id: Optional[str] = None) -> List[AuditLog]:
        """
        特定のアクションの監査ログを取得
        
        Args:
            action (str): アクション名
            limit (int, optional): 取得する最大数
            guild_id (str, optional): 特定のギルドでフィルタ
            
        Returns:
            List[AuditLog]: 監査ログのリスト
        """
        try:
            # クエリの構築
            query = self.session.query(AuditLog).filter(AuditLog.action == action)
            
            if guild_id:
                guild = self.guild_repo.get_guild_by_id(guild_id)
                if guild:
                    query = query.filter(AuditLog.guild_id == guild.id)
            
            # 結果を取得（降順）
            return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"アクション監査ログ取得中にエラー: {e}")
            return []
    
    def get_logs_by_date_range(self, start_date: datetime, end_date: datetime,
                              guild_id: Optional[str] = None, limit: int = 100) -> List[AuditLog]:
        """
        日付範囲での監査ログを取得
        
        Args:
            start_date (datetime): 開始日時
            end_date (datetime): 終了日時
            guild_id (str, optional): 特定のギルドでフィルタ
            limit (int, optional): 取得する最大数
            
        Returns:
            List[AuditLog]: 監査ログのリスト
        """
        try:
            # クエリの構築
            query = self.session.query(AuditLog)\
                .filter(AuditLog.created_at >= start_date)\
                .filter(AuditLog.created_at <= end_date)
            
            if guild_id:
                guild = self.guild_repo.get_guild_by_id(guild_id)
                if guild:
                    query = query.filter(AuditLog.guild_id == guild.id)
            
            # 結果を取得（降順）
            return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"日付範囲での監査ログ取得中にエラー: {e}")
            return []
    
    def get_recent_actions(self, guild_id: str, hours: int = 24, 
                          limit: int = 50) -> List[AuditLog]:
        """
        最近のアクションを取得
        
        Args:
            guild_id (str): DiscordのギルドID
            hours (int, optional): 過去X時間
            limit (int, optional): 取得する最大数
            
        Returns:
            List[AuditLog]: 監査ログのリスト
        """
        try:
            # ギルドを取得
            guild = self.guild_repo.get_guild_by_id(guild_id)
            if not guild:
                logger.warning(f"ギルド {guild_id} が見つかりません")
                return []
            
            # 日時範囲を計算
            start_date = datetime.utcnow() - timedelta(hours=hours)
            
            # クエリの構築
            query = self.session.query(AuditLog)\
                .filter(AuditLog.guild_id == guild.id)\
                .filter(AuditLog.created_at >= start_date)
            
            # 結果を取得（降順）
            return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"最近のアクション取得中にエラー: {e}")
            return [] 