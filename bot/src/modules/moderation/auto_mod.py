import discord
from discord.ext import commands
import logging
import re
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations
from ...config import SPAM_PROTECTION

logger = logging.getLogger('modules.moderation.auto_mod')

class AutoModerator:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.violation_counts = defaultdict(lambda: defaultdict(int))
        self.url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        self.invite_pattern = re.compile(r'discord\.gg/[a-zA-Z0-9]+')
        self.config = self.load_config()
        
        # クリーンアップタスクを開始
        self.bot.loop.create_task(self.cleanup_violations())

    def load_config(self):
        """設定を読み込み"""
        return {
            'max_mentions': SPAM_PROTECTION['mention_limit'],
            'max_emojis': SPAM_PROTECTION['emoji_limit'],
            'max_attachments': SPAM_PROTECTION['attachment_limit'],
            'url_whitelist': SPAM_PROTECTION['url_whitelist'],
            'punishment_thresholds': {
                1: 'warn',
                3: 'mute',
                5: 'kick',
                7: 'ban'
            }
        }

    async def cleanup_violations(self):
        """違反カウントを定期的にリセット"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1時間ごとにリセット
                self.violation_counts.clear()
                logger.info("Cleaned up violation counts")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def check_content(self, message: discord.Message) -> Optional[str]:
        """メッセージの内容をチェック"""
        try:
            # ギルド設定を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(message.guild.id)
                
                if not guild_data or not guild_data.spam_protection:
                    return None

            # 不適切な単語をチェック
            if await self.contains_bad_words(message.content):
                return "bad_words"

            # 悪意のあるURLをチェック
            if await self.contains_malicious_urls(message.content):
                return "malicious_url"

            # 招待リンクをチェック
            if await self.contains_invite_links(message):
                return "invite_link"

            # 添付ファイルをチェック
            if await self.check_attachments(message):
                return "invalid_attachment"

            return None

        except Exception as e:
            logger.error(f"Error in content check: {e}")
            return None

    async def handle_violation(self, message: discord.Message, violation_type: str):
        """違反に対するアクションを実行"""
        try:
            guild_id = message.guild.id
            user_id = message.author.id
            
            # 違反カウントを更新
            self.violation_counts[guild_id][user_id] += 1
            count = self.violation_counts[guild_id][user_id]
            
            # 処罰を決定
            punishment = await self.get_punishment(count)
            
            # メッセージを削除
            await message.delete()
            
            # 処罰を実行
            if punishment == "warn":
                await message.channel.send(
                    f"{message.author.mention} 警告: 不適切なコンテンツが検出されました。",
                    delete_after=10
                )
                
            elif punishment == "mute":
                try:
                    # 10分間のタイムアウト
                    await message.author.timeout(
                        timedelta(minutes=10),
                        reason=f"自動モデレーション: {violation_type}"
                    )
                    await message.channel.send(
                        f"{message.author.mention} 10分間のタイムアウト: 不適切なコンテンツが検出されました。",
                        delete_after=10
                    )
                except discord.Forbidden:
                    logger.warning(f"Failed to timeout user {message.author.id}")
                    
            elif punishment == "kick":
                try:
                    await message.author.kick(
                        reason=f"自動モデレーション: {violation_type}"
                    )
                    await message.channel.send(
                        f"{message.author.mention} をキックしました: 不適切なコンテンツが検出されました。",
                        delete_after=10
                    )
                except discord.Forbidden:
                    logger.warning(f"Failed to kick user {message.author.id}")
                    
            elif punishment == "ban":
                try:
                    await message.author.ban(
                        reason=f"自動モデレーション: {violation_type}",
                        delete_message_days=1
                    )
                    await message.channel.send(
                        f"{message.author.mention} をBANしました: 不適切なコンテンツが検出されました。",
                        delete_after=10
                    )
                except discord.Forbidden:
                    logger.warning(f"Failed to ban user {message.author.id}")
            
            # データベースにログを記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.log_spam(
                    user_id=message.author.id,
                    guild_id=message.guild.id,
                    channel_id=message.channel.id,
                    message_content=message.content,
                    detection_type=violation_type,
                    action_taken=punishment
                )
            
        except Exception as e:
            logger.error(f"Error handling violation: {e}")

    async def contains_bad_words(self, content: str) -> bool:
        """不適切な単語をチェック"""
        # TODO: 不適切な単語リストの実装
        return False

    async def contains_malicious_urls(self, content: str) -> bool:
        """悪意のあるURLをチェック"""
        urls = self.url_pattern.findall(content)
        if not urls:
            return False
            
        for url in urls:
            # ホワイトリストチェック
            if any(domain in url.lower() for domain in self.config['url_whitelist']):
                continue
                
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            return True
            except:
                return True
                
        return False

    async def contains_invite_links(self, message: discord.Message) -> bool:
        """招待リンクをチェック"""
        # 管理者は除外
        if message.author.guild_permissions.administrator:
            return False
            
        # 招待リンクを検索
        if self.invite_pattern.search(message.content):
            return True
            
        return False

    async def check_attachments(self, message: discord.Message) -> bool:
        """添付ファイルをチェック"""
        if not message.attachments:
            return False
            
        # 添付ファイル数の制限
        if len(message.attachments) > self.config['max_attachments']:
            return True
            
        # ファイルタイプのチェック
        allowed_types = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm'}
        for attachment in message.attachments:
            file_ext = attachment.filename.split('.')[-1].lower()
            if file_ext not in allowed_types:
                return True
                
        return False

    async def get_punishment(self, violation_count: int) -> str:
        """違反回数に応じた処罰を決定"""
        for threshold, action in sorted(
            self.config['punishment_thresholds'].items(),
            reverse=True
        ):
            if violation_count >= threshold:
                return action
        return "warn" 