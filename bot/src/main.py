#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Shard Bot のメインエントリーポイント
"""

import os
import sys
import logging
import discord
from dotenv import load_dotenv

# プロジェクトのルートパスをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.src.modules.bot_manager import BotManager
from bot.src.api.main import start_api_in_background

# 環境変数のロード
load_dotenv()

# ロギングの設定
def setup_logging():
    """ロギングの設定"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_dir = os.getenv('LOG_DIR', 'logs')
    
    # ログディレクトリがなければ作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ロギングの基本設定
logging.basicConfig(
        level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
            logging.FileHandler(f'{log_dir}/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # サードパーティライブラリのログレベルを調整
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
logger = logging.getLogger('bot')
logger.info('ロギングを設定しました')


def setup_logging():
    """ロギングの設定"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_dir = os.getenv('LOG_DIR', 'logs')
    # ログディレクトリがなければ作成
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ロギングの基本設定
    logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/bot.log'),
                logging.StreamHandler()
            ]
        )
        # サードパーティライブラリのログレベルを調整
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logger = logging.getLogger('bot')
    logger.info('ロギングを設定しました')


def main():
    """メイン関数"""
    # ロギングの設定
    logger = setup_logging()
    logger.info('Shard Bot を起動します')
    
    try:
        # APIサーバーをバックグラウンドで起動
        logger.info('ヘルスチェックAPIを起動しています...')
        start_api_in_background()

        # インテントの設定
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        
        # ボットマネージャーの作成と起動
        bot_manager = BotManager(intents=intents)
        
        # 開発モードの場合の特別な設定
        if os.getenv('DEBUG', 'false').lower() == 'true':
            dev_guild_id = os.getenv('DEV_GUILD_ID')
            if dev_guild_id:
                logger.info(f'開発モード: ギルド {dev_guild_id} にスラッシュコマンドを登録します')
        
        # ボットを実行
        bot_manager.run()
            
    except Exception as e:
        logger.critical(f'起動中に致命的なエラーが発生しました: {e}', exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

