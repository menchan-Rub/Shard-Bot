import logging
import asyncio
import os
from typing import Dict, Any, Optional, List
import discord
from discord.ext import commands
import importlib
from dotenv import load_dotenv

# データベース関連のインポート
from bot.src.db.database import create_tables_if_not_exist
from bot.src.db.models import (
    Guild, GuildSettings, ModerationSettings, 
    AutoResponseSettings, RaidSettings, SpamSettings
)

# モジュールのインポート
from bot.src.modules.ai_moderation import AIModeration
from bot.src.modules.auto_response import AutoResponse
# その他のモジュールのインポート...

# 環境変数のロード
load_dotenv()

class BotManager:
    """ボット全体を管理するクラス"""
    
    def __init__(self, intents: discord.Intents = None):
        """ボットマネージャーの初期化"""
        self.logger = logging.getLogger('bot.manager')
        
        # Discordボットの設定
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            intents.guilds = True
        
        self.bot = commands.Bot(command_prefix=self._get_prefix, intents=intents, help_command=None)
        
        # モジュールの初期化
        self.modules = {}
        self.ai_moderation = None
        self.auto_response = None
        # その他のモジュール...
        
        # ボットのイベントハンドラを設定
        self._setup_event_handlers()
    
    async def _get_prefix(self, bot: commands.Bot, message: discord.Message) -> str:
        """サーバーごとのプレフィックスを取得"""
        # デフォルトのプレフィックス
        default_prefix = os.getenv('DEFAULT_PREFIX', '!')
        
        # DMの場合はデフォルトのプレフィックスを使用
        if message.guild is None:
            return commands.when_mentioned_or(default_prefix)(bot, message)
        
        # TODO: データベースからギルドのプレフィックスを取得
        # 現在はデフォルトのプレフィックスを返す
        return commands.when_mentioned_or(default_prefix)(bot, message)
    
    def _setup_event_handlers(self):
        """ボットのイベントハンドラを設定"""
        
        @self.bot.event
        async def on_ready():
            """Botが準備完了したときに呼ばれるイベント"""
            self.logger.info(f"ボットとして接続しました: {self.bot.user.name} (ID: {self.bot.user.id})")
            
            # データベースの初期化
            try:
                await create_tables_if_not_exist()
                self.logger.info("データベーステーブルの初期化が完了しました")
            except Exception as e:
                self.logger.error(f"データベース初期化中にエラーが発生しました: {e}")
            
            # モジュールを初期化
            await self._initialize_modules()
            
            # ギルド情報をログに出力
            self.logger.info(f"{len(self.bot.guilds)}個のサーバーに参加しています")
            
            # ステータスを設定
            activity = discord.Activity(type=discord.ActivityType.listening, name="!help")
            await self.bot.change_presence(activity=activity)
        
        @self.bot.event
        async def on_guild_join(guild: discord.Guild):
            """新しいサーバーに参加したときに呼ばれる"""
            self.logger.info(f'新しいサーバーに参加しました: {guild.name} (ID: {guild.id})')
            
            # サーバーの設定をデータベースに登録
            await self._register_guild(guild)
            
            # 自動応答設定を読み込む
            if self.auto_response:
                try:
                    await self.auto_response.load_settings(guild.id)
                    self.logger.info(f'ギルド {guild.id} の自動応答設定を読み込みました')
                except Exception as e:
                    self.logger.error(f'ギルド {guild.id} の自動応答設定読み込み中にエラー: {e}')
        
        @self.bot.event
        async def on_guild_remove(guild: discord.Guild):
            """サーバーから削除されたときに呼ばれる"""
            self.logger.info(f'サーバーから削除されました: {guild.name} (ID: {guild.id})')
            
            # TODO: サーバーの設定を非アクティブにする処理
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """メッセージが送信されたときに呼ばれる"""
            # 自分自身のメッセージは無視
            if message.author.id == self.bot.user.id:
                return
            
            # DMの場合はコマンド処理のみを行う
            if message.guild is None:
                await self.bot.process_commands(message)
                return
            
            # モジュールにメッセージを渡す
            if self.ai_moderation:
                should_continue = await self.ai_moderation.process_message(message)
                if not should_continue:
                    return
            
            if self.auto_response:
                await self.auto_response.process_message(message)
            
            # コマンド処理
            await self.bot.process_commands(message)
    
    async def _initialize_modules(self):
        """モジュールを初期化"""
        # AIモデレーションモジュールの初期化
        self.ai_moderation = AIModeration(self.bot)
        self.modules['ai_moderation'] = self.ai_moderation
        
        # 自動応答モジュールの初期化
        self.auto_response = AutoResponse(self.bot)
        self.modules['auto_response'] = self.auto_response
        
        # その他のモジュール初期化...
        
        self.logger.info('全てのモジュールが初期化されました')
    
    async def _register_guild(self, guild: discord.Guild):
        """サーバーの設定をデータベースに登録"""
        from sqlalchemy.orm import Session
        from bot.src.db.database import get_db_session, get_or_create
        
        # セッション取得
        try:
            with get_db_session() as session:
                # ギルドを登録または取得
                db_guild, created = get_or_create(
                    session,
                    Guild,
                    discord_id=str(guild.id)
                )
                
                # 既存のギルドの場合は情報を更新
                db_guild.name = guild.name
                db_guild.icon_url = str(guild.icon.url) if guild.icon else None
                db_guild.owner_id = str(guild.owner_id) if guild.owner_id else None
                db_guild.member_count = guild.member_count
                
                # 初回の場合は各種設定を作成
                if created:
                    # 基本設定
                    guild_settings = GuildSettings(guild=db_guild)
                    session.add(guild_settings)
                    
                    # モデレーション設定
                    moderation_settings = ModerationSettings(guild=db_guild)
                    session.add(moderation_settings)
                    
                    # 自動応答設定
                    auto_response_settings = AutoResponseSettings(guild=db_guild)
                    session.add(auto_response_settings)
                    
                    # Raid対策設定
                    raid_settings = RaidSettings(guild=db_guild)
                    session.add(raid_settings)
                    
                    # スパム対策設定
                    spam_settings = SpamSettings(guild=db_guild)
                    session.add(spam_settings)
                    
                    self.logger.info(f'サーバーの初期設定を作成しました: {guild.name}')
                
                # コミットはコンテキストマネージャが自動的に行います
        except Exception as e:
            self.logger.error(f'サーバー設定の登録中にエラーが発生しました: {e}')
    
    async def load_extension(self, extension: str) -> bool:
        """拡張機能を読み込む"""
        try:
            await self.bot.load_extension(extension)
            self.logger.info(f'拡張機能を読み込みました: {extension}')
            return True
        except Exception as e:
            self.logger.error(f'拡張機能の読み込みに失敗しました: {extension}\n{type(e).__name__}: {e}')
            return False
    
    async def sync_guild_settings(self, guild_id: int):
        """サーバーの設定をデータベースと同期"""
        from sqlalchemy.orm import Session
        from bot.src.db.database import get_db_session
        
        # セッション取得
        session = get_db_session()
        try:
            # ギルドを取得
            db_guild = session.query(Guild).filter_by(discord_id=str(guild_id)).first()
            if not db_guild:
                self.logger.warning(f'サーバー設定の同期: サーバーが見つかりません (ID: {guild_id})')
                return
            
            # モジュールに設定を反映
            if self.ai_moderation and db_guild.moderation_settings:
                await self.ai_moderation.update_settings(guild_id, db_guild.moderation_settings)
            
            if self.auto_response and db_guild.auto_response_settings:
                await self.auto_response.update_settings(guild_id, db_guild.auto_response_settings)
            
            # その他のモジュール設定の同期...
            
            self.logger.info(f'サーバー設定を同期しました (ID: {guild_id})')
            
        except Exception as e:
            self.logger.error(f'サーバー設定の同期中にエラーが発生しました: {e}')
        finally:
            session.close()
    
    async def register_commands(self, guild_id: Optional[int] = None):
        """スラッシュコマンドを登録"""
        if guild_id:
            # 特定のギルドにコマンドを登録（開発用）
            guild = discord.Object(id=guild_id)
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
            self.logger.info(f'ギルド {guild_id} にスラッシュコマンドを登録しました')
        else:
            # グローバルコマンドとして登録
            await self.bot.tree.sync()
            self.logger.info('グローバルスラッシュコマンドを登録しました')
    
    async def start(self):
        """ボットを起動"""
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            self.logger.error('DISCORD_BOT_TOKENが環境変数に設定されていません')
            return
        
        # コマンド拡張を読み込む
        command_extensions = [
            'bot.src.commands.general_commands',
            'bot.src.commands.mod_commands',
            'bot.src.commands.auto_response.response_commands',
            # その他のコマンド拡張...
        ]
        
        for extension in command_extensions:
            await self.load_extension(extension)
        
        # ボットを起動
        self.logger.info('ボットを起動しています...')
        await self.bot.start(token)
    
    def run(self):
        """ボットを実行（同期版）"""
        asyncio.run(self.start()) 