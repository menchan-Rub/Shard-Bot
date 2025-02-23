from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import logging
from config import DATABASE_CONFIG

# ロガーの設定
logger = logging.getLogger('database')

# 同期エンジンの作成
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 非同期エンジンの作成
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)

# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)

# スコープ付きセッション
db = scoped_session(SessionLocal)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """非同期データベースセッションを取得します"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()

def init_db():
    """データベースの初期化を行います"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")

def get_session():
    """同期セッションを取得します"""
    session = SessionLocal()
    try:
        return session
    except Exception as e:
        session.close()
        logger.error(f"Failed to get database session: {e}")
        raise

async def check_connection():
    """データベース接続を確認します"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False 