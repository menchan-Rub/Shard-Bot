from discord.ext import commands
import discord
import logging
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
import re
import time

# モジュールのインポートエラーを処理
try:
    from modules.moderation.spam_detection import SpamDetector
    spam_detector_available = True
except ImportError:
    spam_detector_available = False

try:
    from database.database_connection import get_db
    from database.database_operations import DatabaseOperations
    database_available = True
except ImportError:
    database_available = False

try:
    from modules.logging.message_logger import MessageLogger
    logger_available = True
except ImportError:
    logger_available = False

try:
    from modules.moderation.auto_mod import AutoModerator
    auto_mod_available = True
except ImportError:
    auto_mod_available = False

logger = logging.getLogger('events.message')

class MessageEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # 利用可能な場合のみインスタンス化
        if spam_detector_available:
            self.spam_detector = SpamDetector(bot)
        else:
            self.spam_detector = None
            logger.warning("SpamDetectorモジュールが利用できないため、スパム検出は無効化されます。")
            
        if auto_mod_available:
            self.auto_moderator = AutoModerator(bot)
        else:
            self.auto_moderator = None
            logger.warning("AutoModeratorモジュールが利用できないため、自動モデレーションは無効化されます。")
            
        if logger_available:
            self.message_logger = MessageLogger(bot)
        else:
            self.message_logger = None
            logger.warning("MessageLoggerモジュールが利用できないため、メッセージログ記録は無効化されます。")
        
        # メッセージ履歴の追跡
        self.message_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.mention_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        
        # クリーンアップタスクを開始
        self.bot.loop.create_task(self.cleanup_history())
        self.ready = asyncio.Event()
        self.bot.loop.create_task(self._setup())

    async def _setup(self):
        """初期化処理"""
        try:
            await self.bot.wait_until_ready()
            self.ready.set()
            logger.info("Message events initialized")
        except Exception as e:
            logger.error(f"Error in message events setup: {e}")
            self.ready.set()

    async def cleanup_history(self):
        """古いメッセージ履歴を定期的にクリーンアップ"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分ごとにクリーンアップ
                current_time = datetime.utcnow()
                
                # メッセージ履歴のクリーンアップ
                for guild_id in list(self.message_history.keys()):
                    for user_id in list(self.message_history[guild_id].keys()):
                        self.message_history[guild_id][user_id] = [
                            time for time in self.message_history[guild_id][user_id]
                            if current_time - time < timedelta(minutes=5)
                        ]
                        if not self.message_history[guild_id][user_id]:
                            del self.message_history[guild_id][user_id]
                    if not self.message_history[guild_id]:
                        del self.message_history[guild_id]
                
                # メンション履歴のクリーンアップ
                for guild_id in list(self.mention_history.keys()):
                    for user_id in list(self.mention_history[guild_id].keys()):
                        self.mention_history[guild_id][user_id] = [
                            time for time in self.mention_history[guild_id][user_id]
                            if current_time - time < timedelta(minutes=5)
                        ]
                        if not self.mention_history[guild_id][user_id]:
                            del self.mention_history[guild_id][user_id]
                    if not self.mention_history[guild_id]:
                        del self.mention_history[guild_id]
                        
                logger.info("Cleaned up message history")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def check_mention_spam(self, message: discord.Message) -> Tuple[bool, str]:
        """メンションスパムをチェック"""
        try:
            guild_id = message.guild.id
            user_id = message.author.id
            current_time = datetime.utcnow()
            
            # メンション数をカウント
            mention_count = len(message.mentions) + len(message.role_mentions)
            if mention_count > 5:  # 1メッセージ内の制限
                return True, "メッセージ内のメンション数が多すぎます"
            
            # メンション履歴を更新
            self.mention_history[guild_id][user_id].append(current_time)
            
            # 5分以内のメンション回数をチェック
            recent_mentions = [
                time for time in self.mention_history[guild_id][user_id]
                if current_time - time < timedelta(minutes=5)
            ]
            
            if len(recent_mentions) > 15:  # 5分間の制限
                return True, "メンションの頻度が高すぎます"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error in mention spam check: {e}")
            return False, ""

    async def check_message_frequency(self, message: discord.Message) -> Tuple[bool, str]:
        """メッセージ送信頻度をチェック"""
        try:
            guild_id = message.guild.id
            user_id = message.author.id
            current_time = datetime.utcnow()
            
            # メッセージ履歴を更新
            self.message_history[guild_id][user_id].append(current_time)
            
            # 5秒以内のメッセージ数をチェック
            recent_messages = [
                time for time in self.message_history[guild_id][user_id]
                if current_time - time < timedelta(seconds=5)
            ]
            
            if len(recent_messages) > 5:  # 5秒間に5メッセージの制限
                return True, "メッセージの送信頻度が高すぎます"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error in message frequency check: {e}")
            return False, ""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージ送信イベントのハンドラ"""
        await self.ready.wait()
        
        try:
            # BOTのメッセージは無視
            if message.author.bot:
                return

            # DMは無視
            if not message.guild:
                return

            # データベースが利用可能な場合のみギルド設定を取得
            if database_available:
                try:
                    async for session in get_db():
                        db = DatabaseOperations(session)
                        guild_data = await db.get_guild(message.guild.id)
                        
                        if not guild_data:
                            return
                            
                        # スパム対策が無効な場合はスキップ
                        if not guild_data.spam_protection:
                            return
                except Exception as e:
                    logger.error(f"データベース操作中にエラーが発生しました: {e}")

            # スパム検出が利用可能な場合のみスパムチェック
            if spam_detector_available and self.spam_detector:
                try:
                    is_spam, detection_type, action = await self.spam_detector.check_message(message)
                    if is_spam:
                        await self.spam_detector.take_action(message, detection_type, action)
                        return
                except Exception as e:
                    logger.error(f"スパム検出中にエラーが発生しました: {e}")

            # メンションスパムチェック
            is_mention_spam, mention_reason = await self.check_mention_spam(message)
            if is_mention_spam:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} 警告: {mention_reason}",
                    delete_after=10
                )
                return

            # メッセージ頻度チェック
            is_frequent, frequency_reason = await self.check_message_frequency(message)
            if is_frequent:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} 警告: {frequency_reason}",
                    delete_after=10
                )
                return

            # 自動モデレーションが利用可能な場合のみ実行
            if auto_mod_available and self.auto_moderator:
                try:
                    violation = await self.auto_moderator.check_content(message)
                    if violation:
                        await self.auto_moderator.handle_violation(message, violation)
                        return
                except Exception as e:
                    logger.error(f"自動モデレーション中にエラーが発生しました: {e}")

            # メッセージログが利用可能な場合のみログ記録
            if logger_available and self.message_logger:
                try:
                    await self.message_logger.log_message(message)
                except Exception as e:
                    logger.error(f"メッセージログ記録中にエラーが発生しました: {e}")

        except Exception as e:
            logger.error(f"Error in message event handler: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集イベントのハンドラ"""
        await self.ready.wait()
        
        try:
            # BOTのメッセージは無視
            if after.author.bot:
                return

            # 内容が変更されていない場合は無視
            if before.content == after.content:
                return

            # 自動モデレーションが利用可能な場合のみ実行
            if auto_mod_available and self.auto_moderator:
                try:
                    violation = await self.auto_moderator.check_content(after)
                    if violation:
                        await self.auto_moderator.handle_violation(after, violation)
                        return
                except Exception as e:
                    logger.error(f"自動モデレーション中にエラーが発生しました: {e}")

            # メッセージログが利用可能な場合のみログ記録
            if logger_available and self.message_logger:
                try:
                    await self.message_logger.log_message_edit(before, after)
                except Exception as e:
                    logger.error(f"メッセージログ記録中にエラーが発生しました: {e}")

        except Exception as e:
            logger.error(f"Error in message edit event handler: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """メッセージ削除イベントのハンドラ"""
        await self.ready.wait()
        
        try:
            # BOTのメッセージは無視
            if message.author.bot:
                return

            # メッセージログが利用可能な場合のみログ記録
            if logger_available and self.message_logger:
                try:
                    await self.message_logger.log_message_delete(message)
                except Exception as e:
                    logger.error(f"メッセージログ記録中にエラーが発生しました: {e}")

        except Exception as e:
            logger.error(f"Error in message delete event handler: {e}")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        """メッセージ一括削除イベントのハンドラ"""
        await self.ready.wait()
        
        try:
            # メッセージログが利用可能な場合のみログ記録
            if logger_available and self.message_logger:
                try:
                    await self.message_logger.log_bulk_message_delete(messages)
                except Exception as e:
                    logger.error(f"メッセージログ記録中にエラーが発生しました: {e}")

        except Exception as e:
            logger.error(f"Error in bulk message delete event handler: {e}")

    async def cog_before_invoke(self, ctx):
        """コマンド実行前に初期化完了を待機"""
        await self.ready.wait()

async def setup(bot: commands.Bot):
    """Cogを登録"""
    try:
        await bot.add_cog(MessageEvents(bot))
        return True
    except Exception as e:
        logger.error(f"MessageEventsCogの登録中にエラーが発生しました: {e}")
        return True  # エラーが発生しても明示的にTrueを返す