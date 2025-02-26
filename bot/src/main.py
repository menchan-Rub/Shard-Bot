import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os
from typing import Optional, Dict, Any, Tuple
import yaml
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import signal
import traceback
from concurrent.futures import ThreadPoolExecutor
from discord import app_commands

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8', mode='a')
    ]
)
logger = logging.getLogger('ShardBot')

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# 環境変数の読み込み
load_dotenv()

# スレッドプールの設定
thread_pool = ThreadPoolExecutor(max_workers=4)

# 環境変数のバリデーション
def validate_env_vars():
    required_vars = ['DISCORD_TOKEN', 'SETUP_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set them in your .env file"
        )

# 設定ファイルの読み込み
def load_config(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class ShardBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            help_command=None,
            max_messages=10000,
            chunk_guilds_at_startup=False,
        )
        self.logger = logger
        self._exit = asyncio.Event()
        self.error_channel_id = int(os.getenv('ERROR_LOG_CHANNEL_ID', 0))
        self._cleanup_tasks = set()  # クリーンアップタスクの追跡用
        self._presence_task = None  # Rich Presence更新タスク用
        
    async def setup_hook(self) -> None:
        """ボットの初期設定を行います"""
        try:
            # エラーロガーの初期化
            from modules.logging.error_logger import ErrorLogger
            self.error_logger = ErrorLogger(self)
            
            # コマンドの読み込み
            await self.load_extensions()
            
            # スラッシュコマンドを同期
            self.logger.info("Syncing slash commands...")
            await self.tree.sync()
            self.logger.info("Slash commands synced successfully!")
            
            # シグナルハンドラの設定
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._handle_signal)

            # Rich Presence更新タスクを開始
            self._presence_task = self.loop.create_task(self._update_presence())
                
        except Exception as e:
            self.logger.error(f"Setup hook failed: {e}")
            traceback.print_exc()
            await self.close()
            
    async def _update_presence(self):
        """Rich Presenceを定期的に更新します"""
        await self.wait_until_ready()  # ボットの準備が完了するまで待機
        try:
            while not self.is_closed():
                activities = [
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"{len(self.guilds)}サーバー"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.playing,
                        name="Shard-Team"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name="メンバー募集中！"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.listening,
                        name="気軽に参加してください！"
                    )
                ]
                for activity in activities:
                    await self.change_presence(activity=activity)
                    await asyncio.sleep(30)  # 30秒ごとに切り替え
        except Exception as e:
            self.logger.error(f"Presence update error: {e}")
        finally:
            if self._presence_task and not self._presence_task.done():
                self._presence_task.cancel()

    async def close(self):
        """ボットのクリーンアップと終了処理"""
        self.logger.info("Shutting down bot...")
        
        # 実行中のタスクをキャンセル
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # スレッドプールのシャットダウン
        thread_pool.shutdown(wait=False)
        
        # 親クラスのclose処理を実行
        await super().close()
        
        self.logger.info("Bot shutdown complete.")

    def _handle_signal(self, signum, frame):
        """シグナルハンドラ"""
        self.logger.info(f"Received signal {signum}")
        
        # asyncio.run()を使用してclose()を実行
        async def cleanup():
            await self.close()
            
        try:
            asyncio.run(cleanup())
        except RuntimeError:
            # イベントループが既に実行中の場合
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        
        # 終了フラグを設定
        self._exit.set()
        
    async def load_extensions(self):
        """全ての拡張機能を読み込みます"""
        # 現在のファイルのディレクトリを取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        extension_dirs = ['commands.moderation', 'commands.admin', 'commands.utility', 'events']
        
        for ext_dir in extension_dirs:
            try:
                # 相対パスを絶対パスに変換
                dir_path = os.path.join(current_dir, *ext_dir.split('.'))
                if not os.path.exists(dir_path):
                    self.logger.warning(f"Directory not found: {dir_path}")
                    continue
                
                for file in os.listdir(dir_path):
                    if file.endswith('.py') and not file.startswith('__'):
                        extension = f"{ext_dir}.{file[:-3]}"
                        try:
                            await self.load_extension(extension)
                            self.logger.info(f'Loaded extension: {extension}')
                        except Exception as e:
                            self.logger.error(f'Failed to load extension {extension}: {e}')
                            self.logger.error(f'Error details: {traceback.format_exc()}')
            except Exception as e:
                self.logger.error(f'Failed to load directory {ext_dir}: {e}')

    async def on_ready(self):
        """ボットが準備完了したときに呼ばれます"""
        self.logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        
        # スラッシュコマンドの状態を確認
        try:
            commands = await self.tree.fetch_commands()
            self.logger.info(f"Registered slash commands: {len(commands)}")
            for cmd in commands:
                self.logger.info(f"- {cmd.name}")
        except Exception as e:
            self.logger.error(f"Failed to fetch slash commands: {e}")
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)}サーバー"
            )
        )
        self.logger.info('------')

    async def send_error_log(self, error: Exception, **context):
        """エラーログをDiscordチャンネルに送信"""
        if not self.error_channel_id:
            return

        channel = self.get_channel(self.error_channel_id)
        if not channel:
            self.logger.error(f"Error log channel (ID: {self.error_channel_id}) not found")
            return

        embed = discord.Embed(
            title="⚠️ エラー発生",
            description=f"```py\n{str(error)}\n```",
            color=0xFF0000,
            timestamp=discord.utils.utcnow()
        )

        # コンテキスト情報を追加
        for key, value in context.items():
            if value:
                embed.add_field(name=key, value=str(value), inline=False)

        # スタックトレースを追加
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(stack_trace) > 1000:
            stack_trace = stack_trace[:997] + "..."
        embed.add_field(name="スタックトレース", value=f"```py\n{stack_trace}\n```", inline=False)

        try:
            await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to send error log: {e}")

    async def on_error(self, event_method: str, *args, **kwargs):
        """グローバルエラーハンドラー"""
        error = sys.exc_info()[1]
        await self.send_error_log(
            error,
            event=event_method,
            guild=kwargs.get('guild'),
            user=kwargs.get('user')
        )
        self.logger.error(f"Error in {event_method}: {error}", exc_info=True)

    async def on_interaction_error(self, interaction: discord.Interaction, error: Exception):
        """インタラクションエラーハンドラー"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"コマンドのクールダウン中です。{error.retry_after:.1f}秒後に再試行してください。",
                ephemeral=True
            )
            return

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
            return

        # Unknown Interactionエラーの特別処理
        if isinstance(error, discord.NotFound) and error.code == 10062:
            self.logger.warning(f"Interaction expired: {interaction.command}")
            return

        # その他のエラー
        await self.send_error_log(
            error,
            command=interaction.command.name if interaction.command else "Unknown",
            guild=interaction.guild,
            user=interaction.user,
            channel=interaction.channel
        )

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "コマンドの実行中にエラーが発生しました。",
                    ephemeral=True
                )
        except Exception:
            pass

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """コマンドエラーハンドラー"""
        if isinstance(error, commands.CommandNotFound):
            return

        await self.send_error_log(
            error,
            command=ctx.command.qualified_name if ctx.command else None,
            guild=ctx.guild,
            user=ctx.author,
            channel=ctx.channel
        )
        self.logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)

    async def generate_captcha(self, length: int = 4) -> Tuple[str, io.BytesIO]:
        """キャプチャ生成（スレッドプールで実行）"""
        def _generate():
            code = ''.join(random.choices(string.digits, k=length))
            width, height = 120, 60
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except Exception:
                font = ImageFont.load_default()
            
            text_width, text_height = draw.textsize(code, font=font)
            x = (width - text_width) / 2
            y = (height - text_height) / 2
            draw.text((x, y), code, font=font, fill=(0, 0, 0))
            
            for _ in range(10):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line(((x1, y1), (x2, y2)), fill=(0, 0, 0), width=1)
            
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            return code, image_bytes
            
        return await asyncio.get_event_loop().run_in_executor(thread_pool, _generate)

    def build_progress_bar(self, current: int, total: int, bar_length: int = 20) -> str:
        """プログレスバーの生成"""
        try:
            filled = int((bar_length * current) // total)
            return "[" + "█" * filled + "░" * (bar_length - filled) + f"] {int(100 * current / total)}%"
        except ZeroDivisionError:
            return "[" + "░" * bar_length + "] 0%"
        except Exception as e:
            self.logger.error(f"Error in progress bar generation: {e}")
            return "[ERROR]"

async def main():
    """メイン関数"""
    try:
        # 環境変数のバリデーション
        validate_env_vars()
        
        # ボットの起動
        bot = ShardBot()
        
        # シグナルハンドラの設定
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: bot._handle_signal(s, f))
        
        async with bot:
            await bot.start(os.getenv('DISCORD_TOKEN'))
            
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        # クリーンアップ処理
        await bot.close()
        # スレッドプールのクリーンアップ
        thread_pool.shutdown(wait=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")
    finally:
        # 残っているタスクをキャンセル
        for task in asyncio.all_tasks():
            task.cancel()
        sys.exit(0) 