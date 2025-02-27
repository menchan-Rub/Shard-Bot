from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

from web.server.config import settings

# メタデータインスタンスの作成（テーブルの再定義を許可）
metadata = MetaData()

# データベースエンジンの作成
engine = create_engine(settings.DATABASE_URL)

# セッションファクトリの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルのベースクラス（テーブルの再定義を許可）
Base = declarative_base(metadata=metadata)
Base.metadata.reflect(bind=engine)

# データベースセッションの取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # 既存のテーブルを削除
    Base.metadata.drop_all(bind=engine)
    # テーブルを作成
    Base.metadata.create_all(bind=engine) 