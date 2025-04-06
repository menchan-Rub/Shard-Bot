from typing import TypeVar, Generic, Type, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from bot.src.db.models import Base

logger = logging.getLogger('bot.repository.base')

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """
    リポジトリパターン実装のベースクラス
    全てのリポジトリはこれを継承します
    """
    
    def __init__(self, session: Session, model_class: Type[T]):
        """
        コンストラクタ
        
        Args:
            session (Session): SQLAlchemyセッション
            model_class (Type[T]): リポジトリで扱うモデルクラス
        """
        self.session = session
        self.model_class = model_class
    
    def get_by_id(self, id: int) -> Optional[T]:
        """
        IDによるエンティティの取得
        
        Args:
            id (int): エンティティID
            
        Returns:
            Optional[T]: 見つかったエンティティ、なければNone
        """
        try:
            return self.session.query(self.model_class).filter(self.model_class.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"{self.model_class.__name__}をIDで取得中にエラー: {e}")
            return None
    
    def get_all(self) -> List[T]:
        """
        全エンティティの取得
        
        Returns:
            List[T]: エンティティのリスト
        """
        try:
            return self.session.query(self.model_class).all()
        except SQLAlchemyError as e:
            logger.error(f"{self.model_class.__name__}の全取得でエラー: {e}")
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[T]:
        """
        新規エンティティの作成
        
        Args:
            data (Dict[str, Any]): エンティティ作成データ
            
        Returns:
            Optional[T]: 作成されたエンティティ、失敗時はNone
        """
        try:
            entity = self.model_class(**data)
            self.session.add(entity)
            self.session.commit()
            return entity
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"{self.model_class.__name__}の作成でエラー: {e}")
            return None
    
    def update(self, id: int, data: Dict[str, Any]) -> bool:
        """
        エンティティの更新
        
        Args:
            id (int): 更新対象のエンティティID
            data (Dict[str, Any]): 更新データ
            
        Returns:
            bool: 更新成功はTrue、失敗はFalse
        """
        try:
            entity = self.get_by_id(id)
            if not entity:
                return False
                
            for key, value in data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"{self.model_class.__name__}の更新でエラー: {e}")
            return False
    
    def delete(self, id: int) -> bool:
        """
        エンティティの削除
        
        Args:
            id (int): 削除対象のエンティティID
            
        Returns:
            bool: 削除成功はTrue、失敗はFalse
        """
        try:
            entity = self.get_by_id(id)
            if not entity:
                return False
                
            self.session.delete(entity)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"{self.model_class.__name__}の削除でエラー: {e}")
            return False
    
    def get_by_attribute(self, attr_name: str, attr_value: Any) -> List[T]:
        """
        特定の属性値でエンティティを検索
        
        Args:
            attr_name (str): 属性名
            attr_value (Any): 属性値
            
        Returns:
            List[T]: 一致するエンティティのリスト
        """
        try:
            if not hasattr(self.model_class, attr_name):
                logger.warning(f"{self.model_class.__name__}に属性{attr_name}がありません")
                return []
                
            return self.session.query(self.model_class).filter(
                getattr(self.model_class, attr_name) == attr_value
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"{self.model_class.__name__}の属性検索でエラー: {e}")
            return [] 