from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

# 相対インポートに変更
from ..config import settings

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# メタデータインスタンスの作成（テーブルの再定義を許可）
metadata = MetaData()

try:
    # データベースエンジンの作成
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    # セッションファクトリの作成
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # モデルのベースクラス（テーブルの再定義を許可）
    Base = declarative_base(metadata=metadata)
    Base.metadata.reflect(bind=engine)
    
    logger.info("データベース接続が正常に確立されました。")
except SQLAlchemyError as e:
    logger.error(f"データベース接続エラー: {e}")
    raise

# データベースセッションの取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        # 既存のテーブルを削除
        Base.metadata.drop_all(bind=engine)
        # テーブルを作成
        Base.metadata.create_all(bind=engine)
        logger.info("データベーステーブルが正常に作成されました。")
    except SQLAlchemyError as e:
        logger.error(f"データベーステーブルの作成エラー: {e}")
        raise 