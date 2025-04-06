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
    'status_rotation_interval': int(os.getenv('STATUS_ROTATION_INTERVAL', 30)),  # ステータス回転間隔（秒）
    'error_reporting': os.getenv('ERROR_REPORTING', 'True').lower() == 'true',  # エラーレポート機能の有効化
    'welcome_message': os.getenv('WELCOME_MESSAGE', 'サーバーへようこそ！'),  # デフォルトのウェルカムメッセージ
    'leave_message': os.getenv('LEAVE_MESSAGE', 'さようなら！またお会いしましょう。'),  # 退出メッセージ
    'auto_role_enabled': os.getenv('AUTO_ROLE_ENABLED', 'False').lower() == 'true',  # 自動ロール付与機能
}

# スパム対策設定
SPAM_PROTECTION = {
    'message_rate_limit': 5,  # X秒間にY個以上のメッセージ
    'message_rate_time': 5,
    'message_rate_count': 5,  # X秒間に許可されるメッセージ数
    'message_rate_seconds': 5,  # メッセージレート制限の時間（秒）
    'mention_limit': 5,  # 1メッセージ内のメンション数制限
    'emoji_limit': 20,  # 1メッセージ内の絵文字数制限
    'attachment_limit': 5,  # 1メッセージ内の添付ファイル数制限
    'duplicate_threshold': 3,  # 同一メッセージの連続投稿制限
    'caps_percentage': 70,  # 大文字の割合制限（%）
    'url_whitelist': [
        'discord.com',
        'discordapp.com',
        'discord.gg',
    ],
    'auto_mute_threshold': 3,  # 自動ミュート発動のしきい値（違反回数）
    'mute_duration': 10,  # 自動ミュート時間（分）
    'warn_before_mute': True,  # ミュート前に警告するか
    'cooldown_period': 60,  # クールダウン期間（秒）- この期間後に違反カウントをリセット
    'smart_detection': True,  # 同様のパターンを学習して検出する高度な検出
    'cross_server_protection': False,  # 他サーバーでのスパム履歴も考慮するか
}

# AI モデレーション設定
AI_MODERATION = {
    'enabled': os.getenv('AI_MODERATION_ENABLED', 'False').lower() == 'true',  # AI モデレーション機能の有効化
    'toxicity_threshold': float(os.getenv('TOXICITY_THRESHOLD', '0.8')),  # 毒性検出の閾値（0-1）
    'identity_attack_threshold': float(os.getenv('IDENTITY_ATTACK_THRESHOLD', '0.8')),  # アイデンティティ攻撃の閾値
    'insult_threshold': float(os.getenv('INSULT_THRESHOLD', '0.8')),  # 侮辱の閾値
    'sexual_threshold': float(os.getenv('SEXUAL_THRESHOLD', '0.9')),  # 性的コンテンツの閾値
    'threat_threshold': float(os.getenv('THREAT_THRESHOLD', '0.9')),  # 脅迫の閾値
    'api_key': os.getenv('AI_API_KEY', ''),  # AI サービスの API キー
    'custom_words': os.getenv('CUSTOM_BAD_WORDS', '').split(','),  # カスタム禁止ワード
    'action_on_detect': os.getenv('AI_ACTION', 'warn'),  # 検出時のアクション (warn, delete, mute, kick, ban)
    'notify_mods': os.getenv('NOTIFY_MODS_ON_AI_DETECT', 'True').lower() == 'true',  # モデレーターに通知するか
    'log_detections': True,  # 検出結果をログに記録するか
    'exclusion_roles': [int(id) for id in os.getenv('AI_EXCLUSION_ROLES', '').split(',') if id],  # 除外ロールID
    'exclusion_channels': [int(id) for id in os.getenv('AI_EXCLUSION_CHANNELS', '').split(',') if id],  # 除外チャンネルID
    'auto_learn': True,  # 自動学習機能（誤検出を学習して精度を向上）
}

# 自動応答システム設定
AUTO_RESPONSE = {
    'enabled': os.getenv('AUTO_RESPONSE_ENABLED', 'False').lower() == 'true',  # 自動応答機能の有効化
    'response_chance': float(os.getenv('RESPONSE_CHANCE', '0.1')),  # 応答する確率 (0-1)
    'max_context_length': int(os.getenv('MAX_CONTEXT_LENGTH', '10')),  # コンテキスト履歴の長さ
    'cooldown': int(os.getenv('RESPONSE_COOLDOWN', '60')),  # クールダウン期間（秒）
    'ignore_prefixes': ['!', '?', '/', '.', '-'],  # 無視するプレフィックス（コマンド判定用）
    'ignore_bots': True,  # ボットのメッセージを無視するか
    'custom_responses': {  # カスタム応答パターン
        'hello': ['こんにちは！', 'やあ！', 'お元気ですか？'],
        'help': ['何かお手伝いできることはありますか？', 'どうしましたか？'],
    },
    'ai_powered': os.getenv('AI_RESPONSE_ENABLED', 'False').lower() == 'true',  # AI パワード応答の有効化
    'ai_model': os.getenv('AI_RESPONSE_MODEL', 'gpt-3.5-turbo'),  # 使用する AI モデル
    'ai_temperature': float(os.getenv('AI_TEMPERATURE', '0.7')),  # AI 応答の温度（創造性）
    'ai_persona': os.getenv('AI_PERSONA', 'あなたはフレンドリーで役立つアシスタントです。'),  # AI のペルソナ設定
}

# レイド対策設定
RAID_PROTECTION = {
    'new_account_threshold': 7,  # アカウント作成からの日数
    'join_rate_limit': 10,  # X秒間にY人以上の参加
    'join_rate_time': 60,
    'suspicious_patterns': [
        r'discord\.gg/[a-zA-Z0-9]+',  # 招待リンク
        r'https?://[^\s]+',  # URL
    ],
    'raid_mode_trigger_count': 15,  # レイドモード発動のための新規参加者数しきい値
    'raid_mode_trigger_time': 120,  # この秒数内の参加でレイドモードが発動（秒）
    'raid_mode_duration': 30,  # レイドモードの継続時間（分）
    'raid_verification_level': 'high',  # レイドモード中の検証レベル（low, medium, high, extreme）
    'auto_action': 'captcha',  # 自動アクション（none, captcha, kick, ban）
    'notify_admins': True,  # 管理者に通知するか
    'lockdown_channels': True,  # チャンネルをロックダウンするか
    'recovery_mode': True,  # 自動復旧モード（レイド終了後に設定を戻す）
    'ip_logging': False,  # IPアドレスログ記録（法的要件に注意）
}

# リアクションロール設定
REACTION_ROLES = {
    'enabled': os.getenv('REACTION_ROLES_ENABLED', 'True').lower() == 'true',  # リアクションロール機能の有効化
    'max_per_message': int(os.getenv('MAX_ROLES_PER_MESSAGE', '20')),  # 1つのメッセージあたりの最大ロール数
    'remove_on_unreact': True,  # リアクション削除時にロールも削除するか
    'dm_on_add': False,  # ロール追加時にDMで通知するか
    'dm_on_remove': False,  # ロール削除時にDMで通知するか
    'exclusive_groups': {},  # 排他的グループ（各グループ内では1つのロールのみ付与可能）
    'add_remove_reactions': True,  # メッセージ追加/削除のリアクションを含めるか
    'timeout': 5,  # リアクション処理のタイムアウト（秒）
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
        'voice_state_update',  # ボイスチャンネルの状態変更ログ
        'invite_create',  # 招待作成ログ
        'invite_delete',  # 招待削除ログ
        'reaction_add',  # リアクション追加ログ
        'reaction_remove',  # リアクション削除ログ
        'message_bulk_delete',  # メッセージ一括削除ログ
    ],
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'log_retention_days': 30,  # ログ保持期間（日）
    'separate_log_files': True,  # イベントタイプごとに別ファイルにログを保存
    'rich_embed_logs': True,  # Discordチャンネルに送信する際にリッチエンベッドを使用
    'log_user_ids': True,  # ユーザーIDをログに記録
}

# 音声チャンネル設定
VOICE_CONFIG = {
    'enabled': os.getenv('VOICE_FEATURES_ENABLED', 'False').lower() == 'true',  # 音声機能の有効化
    'auto_create_channels': os.getenv('AUTO_CREATE_VOICE_CHANNELS', 'False').lower() == 'true',  # 自動チャンネル作成
    'template_name': os.getenv('VOICE_CHANNEL_TEMPLATE', '🔊 {user}のボイスチャンネル'),  # チャンネル名テンプレート
    'template_channels': [int(id) for id in os.getenv('VOICE_TEMPLATE_CHANNELS', '').split(',') if id],  # テンプレートチャンネルID
    'bitrate': int(os.getenv('DEFAULT_BITRATE', '64000')),  # デフォルトのビットレート
    'user_limit': int(os.getenv('DEFAULT_USER_LIMIT', '0')),  # デフォルトのユーザー制限（0は無制限）
    'auto_delete': True,  # 空になった場合に自動削除するか
    'delete_delay': 10,  # 削除までの遅延時間（秒）
    'allow_rename': True,  # ユーザーによる名前変更を許可するか
    'allow_limit_change': True,  # ユーザーによる制限変更を許可するか
    'allow_bitrate_change': True,  # ユーザーによるビットレート変更を許可するか
    'allow_private': True,  # プライベートチャンネル作成を許可するか
    'admin_role_ids': [int(id) for id in os.getenv('VOICE_ADMIN_ROLES', '').split(',') if id],  # 音声管理者ロールID
}

# Webダッシュボード設定
DASHBOARD_CONFIG = {
    'client_id': os.getenv('DISCORD_CLIENT_ID'),
    'client_secret': os.getenv('DISCORD_CLIENT_SECRET'),
    'redirect_uri': os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:3000/callback'),
    'api_endpoint': os.getenv('API_ENDPOINT', 'http://localhost:8000'),
    'session_secret': os.getenv('SESSION_SECRET', 'your-secret-key'),
    'jwt_expiration': int(os.getenv('JWT_EXPIRATION', '86400')),  # JWT有効期間（秒）
    'allowed_origins': os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(','),  # CORSオリジン
    'require_2fa': os.getenv('REQUIRE_2FA', 'False').lower() == 'true',  # 管理者に2FA要求
    'analytics_enabled': os.getenv('ANALYTICS_ENABLED', 'True').lower() == 'true',  # 分析機能の有効化
    'theme': os.getenv('DASHBOARD_THEME', 'dark'),  # デフォルトテーマ
    'logo_url': os.getenv('DASHBOARD_LOGO', ''),  # カスタムロゴURL
    'support_email': os.getenv('SUPPORT_EMAIL', ''),  # サポート用メールアドレス
}

# イベント管理システム
EVENT_SYSTEM = {
    'enabled': os.getenv('EVENT_SYSTEM_ENABLED', 'False').lower() == 'true',  # イベント管理機能の有効化
    'max_events_per_guild': int(os.getenv('MAX_EVENTS_PER_GUILD', '10')),  # ギルドあたりの最大イベント数
    'event_categories': ['meeting', 'game', 'tournament', 'other'],  # イベントカテゴリ
    'allow_rsvp': True,  # RSVP（参加・不参加）機能を有効にするか
    'reminder_times': [60, 10],  # リマインダー送信時間（分前）
    'create_voice_channel': True,  # イベント用ボイスチャンネルを作成するか
    'create_text_channel': True,  # イベント用テキストチャンネルを作成するか
    'auto_delete_channels': True,  # イベント終了後にチャンネルを削除するか
    'default_duration': 60,  # デフォルトのイベント時間（分）
    'calendar_integration': os.getenv('CALENDAR_INTEGRATION', 'False').lower() == 'true',  # カレンダー連携
    'calendar_api_key': os.getenv('CALENDAR_API_KEY', ''),  # カレンダーAPIキー
}

def get_config() -> Dict[str, Any]:
    """全ての設定を取得します"""
    return {
        'database': DATABASE_CONFIG,
        'bot': BOT_CONFIG,
        'spam_protection': SPAM_PROTECTION,
        'ai_moderation': AI_MODERATION,
        'auto_response': AUTO_RESPONSE,
        'raid_protection': RAID_PROTECTION,
        'reaction_roles': REACTION_ROLES,
        'logging': LOGGING_CONFIG,
        'voice': VOICE_CONFIG,
        'dashboard': DASHBOARD_CONFIG,
        'event_system': EVENT_SYSTEM,
    } 