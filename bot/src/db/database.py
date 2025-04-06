import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv

# 環境変数のロード
load_dotenv()

# ロガーの設定
logger = logging.getLogger('bot.database')

# 環境変数から接続情報を取得
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'shardbot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_SSL_MODE = os.getenv('DB_SSL_MODE', 'disable')

# SQLAlchemy接続URL
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# エンジンの作成
engine = create_engine(
    DB_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    poolclass=QueuePool,
    connect_args={
        'sslmode': 'disable',  # SSLを無効化
        'connect_timeout': 10
    }
)

# セッションファクトリを作成
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

# モデルのベースクラス
Base = declarative_base()
Base.query = Session.query_property()

def init_db() -> None:
    """
    データベースとテーブルを初期化します。
    既存のテーブルがある場合は何もしません。
    """
    try:
        logger.info("データベース初期化処理を開始中...")
        Base.metadata.create_all(engine)
        logger.info("データベースの初期化が完了しました")
    except Exception as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        raise

@contextmanager
def get_db_session() -> Generator:
    """
    データベースセッションのコンテキストマネージャー。
    with文で使用すると、セッションを自動的にクローズします。
    
    Example:
        with get_db_session() as session:
            guilds = session.query(Guild).all()
    
    Yields:
        Generator: SQLAlchemyのセッションオブジェクト
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"データベースセッション中にエラーが発生しました: {e}")
        raise
    finally:
        session.close()

async def get_guild_settings(guild_id: str):
    """
    ギルドの設定を取得します。
    存在しない場合はデフォルト設定を返します。
    
    Args:
        guild_id (str): DiscordギルドID
    
    Returns:
        GuildSettings: ギルドの設定
    """
    from bot.src.db.models import Guild, GuildSettings
    
    with get_db_session() as session:
        # ギルドを検索
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        
        # ギルドが存在しない場合は新規作成
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()  # IDを生成するためにフラッシュ
            
            # デフォルト設定を作成
            settings = GuildSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            return settings
        
        # 既存のギルドに設定がない場合は新規作成
        if not guild.settings:
            settings = GuildSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            return settings
            
        return guild.settings

async def get_ai_mod_settings(guild_id: str):
    """
    ギルドのAIモデレーション設定を取得します。
    存在しない場合はデフォルト設定を返します。
    
    Args:
        guild_id (str): DiscordギルドID
    
    Returns:
        AIModSettings: AIモデレーション設定
    """
    from bot.src.db.models import Guild, AIModSettings
    
    with get_db_session() as session:
        # ギルドを検索
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        
        # ギルドが存在しない場合は新規作成
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()  # IDを生成するためにフラッシュ
        
        # 既存のギルドにAIモデレーション設定がない場合は新規作成
        if not guild.ai_mod_settings:
            settings = AIModSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            return settings
            
        return guild.ai_mod_settings

async def get_auto_response_settings(guild_id: str):
    """
    ギルドの自動応答設定を取得します。
    存在しない場合はデフォルト設定を返します。
    
    Args:
        guild_id (str): DiscordギルドID
    
    Returns:
        AutoResponseSettings: 自動応答設定
    """
    from bot.src.db.models import Guild, AutoResponseSettings
    
    with get_db_session() as session:
        # ギルドを検索
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        
        # ギルドが存在しない場合は新規作成
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()  # IDを生成するためにフラッシュ
        
        # 既存のギルドに自動応答設定がない場合は新規作成
        if not guild.auto_response_settings:
            settings = AutoResponseSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            # オブジェクトをデタッチする前に必要な属性を全て読み込む
            settings_dict = {
                'id': settings.id,
                'guild_id': settings.guild_id,
                'enabled': settings.enabled,
                'response_chance': settings.response_chance,
                'cooldown': settings.cooldown,
                'max_context_length': settings.max_context_length,
                'ignore_bots': settings.ignore_bots,
                'ignore_prefixes': settings.ignore_prefixes,
                'ai_enabled': settings.ai_enabled,
                'ai_temperature': settings.ai_temperature,
                'ai_persona': settings.ai_persona,
                'custom_responses': settings.custom_responses
            }
            # セッションからデタッチして新しいオブジェクトを返す
            session.expunge(settings)
            return settings
            
        # 既存の設定を読み込んでデタッチ
        settings = guild.auto_response_settings
        # オブジェクトをデタッチする前に必要な属性を全て読み込む
        settings_dict = {
            'id': settings.id,
            'guild_id': settings.guild_id,
            'enabled': settings.enabled,
            'response_chance': settings.response_chance,
            'cooldown': settings.cooldown,
            'max_context_length': settings.max_context_length,
            'ignore_bots': settings.ignore_bots,
            'ignore_prefixes': settings.ignore_prefixes,
            'ai_enabled': settings.ai_enabled,
            'ai_temperature': settings.ai_temperature,
            'ai_persona': settings.ai_persona,
            'custom_responses': settings.custom_responses
        }
        # セッションからデタッチして返す
        session.expunge(settings)
        return settings

async def get_raid_settings(guild_id: str):
    """
    ギルドのレイド保護設定を取得します。
    存在しない場合はデフォルト設定を返します。
    
    Args:
        guild_id (str): DiscordギルドID
    
    Returns:
        RaidSettings: レイド保護設定
    """
    from bot.src.db.models import Guild, RaidSettings
    
    with get_db_session() as session:
        # ギルドを検索
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        
        # ギルドが存在しない場合は新規作成
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()  # IDを生成するためにフラッシュ
        
        # 既存のギルドにレイド保護設定がない場合は新規作成
        if not guild.raid_settings:
            settings = RaidSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            return settings
            
        return guild.raid_settings

async def get_spam_settings(guild_id: str):
    """
    ギルドのスパム保護設定を取得します。
    存在しない場合はデフォルト設定を返します。
    
    Args:
        guild_id (str): DiscordギルドID
    
    Returns:
        SpamSettings: スパム保護設定
    """
    from bot.src.db.models import Guild, SpamSettings
    
    with get_db_session() as session:
        # ギルドを検索
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        
        # ギルドが存在しない場合は新規作成
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()  # IDを生成するためにフラッシュ
        
        # 既存のギルドにスパム保護設定がない場合は新規作成
        if not guild.spam_settings:
            settings = SpamSettings(guild_id=guild.id)
            session.add(settings)
            session.commit()
            return settings
            
        return guild.spam_settings

async def log_audit_event(guild_id: str, user_id: str, action: str, target_id: str = None, 
                        target_type: str = None, details: dict = None):
    """
    監査ログを記録します。
    
    Args:
        guild_id (str): DiscordギルドID
        user_id (str): 実行者のDiscordユーザーID
        action (str): 実行されたアクション
        target_id (str, optional): 対象ID
        target_type (str, optional): 対象タイプ
        details (dict, optional): 詳細情報
    """
    from bot.src.db.models import AuditLog, Guild, User
    
    with get_db_session() as session:
        # ギルドが存在するか確認
        guild = session.query(Guild).filter(Guild.discord_id == guild_id).first()
        if not guild:
            guild = Guild(discord_id=guild_id, name=f"Guild-{guild_id}", owner_id="0")
            session.add(guild)
            session.flush()
        
        # ユーザーが存在するか確認
        user = session.query(User).filter(User.discord_id == user_id).first()
        if not user:
            user = User(discord_id=user_id, username=f"User-{user_id}")
            session.add(user)
            session.flush()
        
        # 監査ログを作成
        log = AuditLog(
            guild_id=guild.id,
            user_id=user.id,
            action=action,
            target_id=target_id,
            target_type=target_type,
            details=details or {}
        )
        
        session.add(log)
        session.commit()
        
        return log.id

def get_redis_url():
    """RedisのURLを取得"""
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = os.getenv('REDIS_PORT', '6379')
    redis_password = os.getenv('REDIS_PASSWORD', '')
    redis_db = os.getenv('REDIS_DB', '0')
    
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

def get_or_create(session, model, **kwargs):
    """指定されたモデルのインスタンスを取得または作成"""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance, True

async def create_tables_if_not_exist():
    """
    データベーステーブルが存在しない場合に作成します。
    """
    try:
        from bot.src.db.models import Base
        
        logger.info("データベーステーブルが存在しないため、作成します")
        # テーブルの作成
        Base.metadata.create_all(engine)
        logger.info("データベーステーブルを作成しました")
        return True
    except Exception as e:
        logger.error(f"テーブル作成中にエラーが発生しました: {e}")
        raise

def close_db_connection():
    """データベース接続を閉じる"""
    Session.remove()
    engine.dispose()
    logger.info("データベース接続を閉じました") 