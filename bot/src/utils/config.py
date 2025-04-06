"""
設定を読み込むためのモジュール
"""
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def get_config() -> Dict[str, Any]:
    """
    設定を読み込む関数
    環境変数 CONFIG_PATH が設定されている場合はそのパスから読み込み
    設定されていない場合はデフォルト設定を返す
    """
    config_path = os.environ.get('CONFIG_PATH')
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"設定ファイルを読み込みました: {config_path}")
                return config
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
    
    # デフォルト設定
    default_config = {
        "cors_origins": [
            "http://localhost:3000", 
            "http://localhost:8080", 
            "http://localhost:5173",
            "*"  # 開発環境用
        ],
        "jwt_secret": os.environ.get("JWT_SECRET", "your-secret-key-change-in-production"),
        "jwt_algorithm": "HS256",
        "jwt_expires_minutes": 60 * 24 * 30,  # 30日間
        "refresh_token_expires_days": 60,  # 60日間
        "api_rate_limit": 100,  # 1分あたりのリクエスト数
        "discord_api_base_url": "https://discord.com/api/v10",
        "logging_level": "INFO",
    }
    
    logger.info("デフォルト設定を使用します")
    return default_config 