import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ロガーの設定
logger = logging.getLogger('ShardBot.Database')

# データベースのベースクラスを定義
Base = declarative_base()

# データベースのURL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///bot.db')

# エンジンとセッションファクトリの作成
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """データベースのテーブルを作成"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("データベーステーブルを作成しました")
    except Exception as e:
        logger.error(f"データベーステーブルの作成に失敗: {e}")
        raise

def init_database():
    """データベースエンジンとセッションファクトリを作成"""
    try:
        logger.info(f"データベースに接続: {DATABASE_URL}")
        return engine, async_session
    except Exception as e:
        logger.error(f"データベースの初期化に失敗: {e}")
        raise

# データベースセッションを取得するコンテキストマネージャ
async def get_db():
    """データベースセッションを取得"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

__all__ = ['Base', 'init_db', 'init_database', 'get_db'] 