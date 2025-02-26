from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base
import os
from dotenv import load_dotenv
import asyncio
import logging

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

if __name__ == "__main__":
    asyncio.run(main()) 