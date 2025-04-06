#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベーステーブル作成スクリプト
"""

import os
import sys
import logging
from dotenv import load_dotenv

# ルートパスをPythonパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# 環境変数のロード
load_dotenv()

# モデルと接続のインポート
from bot.src.db.models import Base
from bot.src.db.database import engine, init_db

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_migration')

def create_tables():
    """データベーステーブルを作成する"""
    try:
        # 全テーブルを作成
        Base.metadata.create_all(bind=engine)
        logger.info("データベーステーブルを正常に作成しました。")
    except Exception as e:
        logger.error(f"テーブル作成中にエラーが発生しました: {e}")
        sys.exit(1)

def drop_tables():
    """データベーステーブルを削除する（危険な操作）"""
    try:
        # 確認
        confirm = input("全てのテーブルを削除します。このアクションは元に戻せません。続行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            logger.info("テーブル削除をキャンセルしました。")
            return
        
        # 全テーブルを削除
        Base.metadata.drop_all(bind=engine)
        logger.info("データベーステーブルを正常に削除しました。")
    except Exception as e:
        logger.error(f"テーブル削除中にエラーが発生しました: {e}")
        sys.exit(1)

def recreate_tables():
    """テーブルを再作成する（危険な操作）"""
    try:
        # 確認
        confirm = input("全てのテーブルを削除して再作成します。全てのデータが失われます。続行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            logger.info("テーブル再作成をキャンセルしました。")
            return
        
        # 全テーブルを削除して再作成
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("データベーステーブルを正常に再作成しました。")
    except Exception as e:
        logger.error(f"テーブル再作成中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='データベースマイグレーションスクリプト')
    parser.add_argument('action', choices=['create', 'drop', 'recreate'],
                        help='実行するアクション（create: テーブル作成, drop: テーブル削除, recreate: テーブル再作成）')
    
    args = parser.parse_args()
    
    # 指定されたアクションを実行
    if args.action == 'create':
        create_tables()
    elif args.action == 'drop':
        drop_tables()
    elif args.action == 'recreate':
        recreate_tables() 