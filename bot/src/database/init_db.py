import os
import sys
from pathlib import Path

# プロジェクトルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from web.server.database.database import Base
import asyncio
import logging
from dotenv import load_dotenv

from web.server.models import (
    User,
    Settings,
    AuditLog,
    SpamLog,
    Guild,
    Warning,
    Role,
    Channel,
)

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# データベース接続情報
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# 非同期エンジンの作成
async_engine = create_async_engine(DATABASE_URL)

async def init_db():
    """データベースを初期化し、必要なテーブルを作成します"""
    try:
        # テーブルの作成
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("データベースの初期化が完了しました。")
    except Exception as e:
        logger.error(f"データベースの初期化中にエラーが発生しました: {e}")
        raise

async def main():
    """メイン関数"""
    await init_db()

def init_database():
    # データベースエンジンの作成
    engine = create_engine(DATABASE_URL)
    
    # テーブルの作成
    Base.metadata.create_all(bind=engine)
    
    # セッションファクトリの作成
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("データベースの初期化が完了しました。")

if __name__ == "__main__":
    asyncio.run(main())
    init_database() 