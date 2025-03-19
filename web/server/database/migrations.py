import os
import sys
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, MetaData, Table
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.server.database.database import engine, Base, metadata
from web.server.models.settings import BotSettings
from web.server.models.user import User

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """データベースマイグレーションを実行する"""
    try:
        logger.info("マイグレーションを開始します...")
        
        # 既存テーブルの確認
        inspector = engine.dialect.inspector
        existing_tables = inspector.get_table_names()
        
        # BotSettings テーブルの作成（存在しない場合）
        if "bot_settings" not in existing_tables:
            logger.info("BotSettings テーブルを作成します...")
            
            # テーブル定義
            bot_settings_table = Table(
                "bot_settings",
                metadata,
                Column("id", Integer, primary_key=True, index=True),
                Column("guild_id", String, index=True),
                Column("user_id", Integer, ForeignKey("users.id"), index=True),
                Column("settings", JSON, default={}),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
                extend_existing=True
            )
            
            # テーブル作成
            bot_settings_table.create(engine, checkfirst=True)
            logger.info("BotSettings テーブルが正常に作成されました")
        else:
            logger.info("BotSettings テーブルは既に存在します")
        
        # User モデルに bot_settings リレーションシップを追加
        # (SQLAlchemy のマッピングのみの変更なので、スキーマ変更は不要)
        
        # マイグレーション完了
        logger.info("マイグレーションが正常に完了しました")
        
    except SQLAlchemyError as e:
        logger.error(f"マイグレーションエラー: {e}")
        raise
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}")
        raise

def rollback_migrations():
    """マイグレーションをロールバックする（テスト用）"""
    try:
        logger.warning("マイグレーションをロールバックします...")
        
        # BotSettings テーブルを削除
        if engine.dialect.has_table(engine, "bot_settings"):
            metadata.tables["bot_settings"].drop(engine)
            logger.info("BotSettings テーブルが削除されました")
        
        logger.warning("マイグレーションのロールバックが完了しました")
    except SQLAlchemyError as e:
        logger.error(f"ロールバックエラー: {e}")
        raise
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}")
        raise

if __name__ == "__main__":
    # コマンドライン引数からアクションを取得
    action = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    
    if action == "migrate":
        run_migrations()
    elif action == "rollback":
        rollback_migrations()
    else:
        logger.error(f"不明なアクション: {action}")
        print("使用法: python migrations.py [migrate|rollback]")
        sys.exit(1) 