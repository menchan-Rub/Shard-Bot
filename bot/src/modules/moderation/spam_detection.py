import re
from typing import Dict, List, Set, Optional, Tuple
import discord
from discord.ext import commands
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from database.database_connection import get_db
from database.database_operations import DatabaseOperations
from config import SPAM_PROTECTION

logger = logging.getLogger('modules.moderation.spam_detection')

class SpamDetector:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # メッセージ履歴の追跡
        self.message_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.duplicate_messages: Dict[int, Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.caps_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.emoji_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        
        # 絵文字の正規表現パターン
        self.emoji_pattern = re.compile(r'<a?:\w+:\d+>|[\U0001F300-\U0001F9FF]')
        
        # スパム検出の設定
        self.config = {
            'message_rate': {
                'count': SPAM_PROTECTION['message_rate_count'],
                'seconds': SPAM_PROTECTION['message_rate_seconds']
            },
            'duplicate_threshold': SPAM_PROTECTION['duplicate_threshold'],
            'caps_percentage': SPAM_PROTECTION['caps_percentage'],
            'emoji_limit': SPAM_PROTECTION['emoji_limit'],
            'mention_limit': SPAM_PROTECTION['mention_limit']
        }
        
        # クリーンアップタスクを開始
        self.bot.loop.create_task(self.cleanup_history())

    async def cleanup_history(self):
        """古い履歴を定期的にクリーンアップ"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30分ごとにクリーンアップ
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
                
                # 重複メッセージのクリーンアップ
                self.duplicate_messages.clear()
                
                # 大文字履歴のクリーンアップ
                for guild_id in list(self.caps_history.keys()):
                    for user_id in list(self.caps_history[guild_id].keys()):
                        self.caps_history[guild_id][user_id] = [
                            time for time in self.caps_history[guild_id][user_id]
                            if current_time - time < timedelta(minutes=5)
                        ]
                        if not self.caps_history[guild_id][user_id]:
                            del self.caps_history[guild_id][user_id]
                    if not self.caps_history[guild_id]:
                        del self.caps_history[guild_id]
                
                # 絵文字履歴のクリーンアップ
                for guild_id in list(self.emoji_history.keys()):
                    for user_id in list(self.emoji_history[guild_id].keys()):
                        self.emoji_history[guild_id][user_id] = [
                            time for time in self.emoji_history[guild_id][user_id]
                            if current_time - time < timedelta(minutes=5)
                        ]
                        if not self.emoji_history[guild_id][user_id]:
                            del self.emoji_history[guild_id][user_id]
                    if not self.emoji_history[guild_id]:
                        del self.emoji_history[guild_id]
                
                logger.info("Cleaned up spam detection history")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def check_message(self, message: discord.Message) -> Tuple[bool, str, str]:
        """メッセージをチェックし、スパムかどうかを判定"""
        try:
            # ギルド設定を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(message.guild.id)
                
                if not guild_data or not guild_data.spam_protection:
                    return False, "", ""
            
            user_id = message.author.id
            current_time = datetime.utcnow()
            
            # 管理者は除外
            if message.author.guild_permissions.administrator:
                return False, "", ""

            # メッセージ頻度チェック
            if await self._check_message_rate(message):
                return True, "message_rate", "timeout"

            # 重複メッセージチェック
            if await self._check_duplicate_messages(message):
                return True, "duplicate", "delete"

            # 大文字スパムチェック
            if await self._check_caps_spam(message):
                return True, "caps", "delete"

            # 絵文字スパムチェック
            if await self._check_emoji_spam(message):
                return True, "emoji", "delete"

            # メンションスパムチェック
            if await self._check_mention_spam(message):
                return True, "mention", "timeout"

            return False, "", ""

        except Exception as e:
            logger.error(f"Error in spam check: {e}")
            return False, "", ""

    async def _check_message_rate(self, message: discord.Message) -> bool:
        """メッセージ送信頻度をチェック"""
        try:
            guild_id = message.guild.id
            user_id = message.author.id
            current_time = datetime.utcnow()
            
            # メッセージ履歴を更新
            self.message_history[guild_id][user_id].append(current_time)
            
            # 設定された期間内のメッセージ数をチェック
            recent_messages = [
                time for time in self.message_history[guild_id][user_id]
                if current_time - time < timedelta(seconds=self.config['message_rate']['seconds'])
            ]
            
            return len(recent_messages) > self.config['message_rate']['count']
            
        except Exception as e:
            logger.error(f"Error checking message rate: {e}")
            return False

    async def _check_duplicate_messages(self, message: discord.Message) -> bool:
        """重複メッセージをチェック"""
        try:
            guild_id = message.guild.id
            user_id = message.author.id
            content = message.content.lower()
            
            # 重複メッセージリストを更新
            self.duplicate_messages[guild_id][user_id].append(content)
            
            # 最新の3メッセージをチェック
            recent_messages = self.duplicate_messages[guild_id][user_id][-3:]
            if len(recent_messages) >= 3:
                if all(msg == content for msg in recent_messages):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate messages: {e}")
            return False

    async def _check_caps_spam(self, message: discord.Message) -> bool:
        """大文字スパムをチェック"""
        try:
            if len(message.content) < 10:  # 短いメッセージは無視
                return False
            
            # 大文字の割合を計算
            uppercase_chars = sum(1 for c in message.content if c.isupper())
            total_chars = sum(1 for c in message.content if c.isalpha())
            
            if total_chars == 0:
                return False
            
            caps_ratio = uppercase_chars / total_chars
            if caps_ratio > self.config['caps_percentage']:
                guild_id = message.guild.id
                user_id = message.author.id
                current_time = datetime.utcnow()
                
                # 大文字履歴を更新
                self.caps_history[guild_id][user_id].append(current_time)
                
                # 5分以内の大文字メッセージをチェック
                recent_caps = [
                    time for time in self.caps_history[guild_id][user_id]
                    if current_time - time < timedelta(minutes=5)
                ]
                
                return len(recent_caps) >= 3
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking caps spam: {e}")
            return False

    async def _check_emoji_spam(self, message: discord.Message) -> bool:
        """絵文字スパムをチェック"""
        try:
            # 絵文字の数をカウント
            emoji_count = len(self.emoji_pattern.findall(message.content))
            
            if emoji_count > self.config['emoji_limit']:
                guild_id = message.guild.id
                user_id = message.author.id
                current_time = datetime.utcnow()
                
                # 絵文字履歴を更新
                self.emoji_history[guild_id][user_id].append(current_time)
                
                # 5分以内の絵文字スパムをチェック
                recent_emoji = [
                    time for time in self.emoji_history[guild_id][user_id]
                    if current_time - time < timedelta(minutes=5)
                ]
                
                return len(recent_emoji) >= 3
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking emoji spam: {e}")
            return False

    async def _check_mention_spam(self, message: discord.Message) -> bool:
        """メンションスパムをチェック"""
        try:
            # メンション数をカウント
            mention_count = len(message.mentions) + len(message.role_mentions)
            
            return mention_count > self.config['mention_limit']
            
        except Exception as e:
            logger.error(f"Error checking mention spam: {e}")
            return False

    async def take_action(self, message: discord.Message, detection_type: str, action: str):
        """スパム検出時のアクションを実行"""
        try:
            # メッセージを削除
            await message.delete()
            
            if action == "delete":
                await message.channel.send(
                    f"{message.author.mention} 警告: スパムが検出されました。",
                    delete_after=10
                )
                
            elif action == "timeout":
                try:
                    # 10分間のタイムアウト
                    await message.author.timeout(
                        timedelta(minutes=10),
                        reason=f"スパム検出: {detection_type}"
                    )
                    await message.channel.send(
                        f"{message.author.mention} 10分間のタイムアウト: スパムが検出されました。",
                        delete_after=10
                    )
                except discord.Forbidden:
                    logger.warning(f"Failed to timeout user {message.author.id}")
            
            # データベースにログを記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.log_spam(
                    user_id=message.author.id,
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    message_content=message.content,
                    detection_type=detection_type,
                    action_taken=action
                )
            
        except Exception as e:
            logger.error(f"Error taking action: {e}") 