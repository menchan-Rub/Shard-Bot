import os
from typing import Dict, Any
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# データベース設定
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'shardbot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# ボット設定
BOT_CONFIG = {
    'default_prefix': '!',
    'owner_ids': [int(id) for id in os.getenv('OWNER_IDS', '').split(',') if id],
    'support_server': os.getenv('SUPPORT_SERVER', ''),
}

# スパム対策設定
SPAM_PROTECTION = {
    'message_rate_limit': 5,  # X秒間にY個以上のメッセージ
    'message_rate_time': 5,
    'mention_limit': 5,  # 1メッセージ内のメンション数制限
    'emoji_limit': 20,  # 1メッセージ内の絵文字数制限
    'attachment_limit': 5,  # 1メッセージ内の添付ファイル数制限
    'url_whitelist': [
        'discord.com',
        'discordapp.com',
        'discord.gg',
    ]
}

# レイド対策設定
RAID_PROTECTION = {
    'new_account_threshold': 7,  # アカウント作成からの日数
    'join_rate_limit': 10,  # X秒間にY人以上の参加
    'join_rate_time': 60,
    'suspicious_patterns': [
        r'discord\.gg/[a-zA-Z0-9]+',  # 招待リンク
        r'https?://[^\s]+',  # URL
    ]
}

# ログ設定
LOGGING_CONFIG = {
    'enabled_events': [
        'message_delete',
        'message_edit',
        'member_join',
        'member_remove',
        'member_ban',
        'member_unban',
        'role_create',
        'role_delete',
        'channel_create',
        'channel_delete',
    ],
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
}

# Webダッシュボード設定
DASHBOARD_CONFIG = {
    'client_id': os.getenv('DISCORD_CLIENT_ID'),
    'client_secret': os.getenv('DISCORD_CLIENT_SECRET'),
    'redirect_uri': os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:3000/callback'),
    'api_endpoint': os.getenv('API_ENDPOINT', 'http://localhost:8000'),
    'session_secret': os.getenv('SESSION_SECRET', 'your-secret-key'),
}

def get_config() -> Dict[str, Any]:
    """全ての設定を取得します"""
    return {
        'database': DATABASE_CONFIG,
        'bot': BOT_CONFIG,
        'spam_protection': SPAM_PROTECTION,
        'raid_protection': RAID_PROTECTION,
        'logging': LOGGING_CONFIG,
        'dashboard': DASHBOARD_CONFIG,
    } 