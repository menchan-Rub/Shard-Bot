import discord
from discord.ext import commands
from typing import List, Optional, Dict, Union, Tuple
import logging
import re
from datetime import datetime, timedelta
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.automod')

class AutoModService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_cooldowns = {}
        self.mention_cooldowns = {}
        self.invite_cooldowns = {}
        self.link_cooldowns = {}
        self.caps_cooldowns = {}
        self.emoji_cooldowns = {}

    async def get_automod_settings(self, guild_id: int) -> Dict:
        """
        自動モデレーション設定を取得します。
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                settings = await db.get_automod_settings(guild_id)
                return settings or {}

        except Exception as e:
            logger.error(f"Failed to get automod settings: {e}")
            return {}

    async def update_automod_settings(
        self,
        guild_id: int,
        settings: Dict,
        moderator: discord.Member = None
    ) -> str:
        """
        自動モデレーション設定を更新します。
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.update_automod_settings(guild_id, settings)

                # 監査ログに記録
                await db.create_audit_log(
                    guild_id=guild_id,
                    action_type="update_automod",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=None,
                    reason="自動モデレーション設定を更新",
                    details=settings
                )

            return "自動モデレーション設定を更新しました。"

        except Exception as e:
            logger.error(f"Failed to update automod settings: {e}")
            return "設定の更新中にエラーが発生しました。"

    async def check_message(self, message: discord.Message) -> Optional[str]:
        """
        メッセージをチェックし、違反があれば理由を返します。
        """
        if message.author.bot or not message.guild:
            return None

        try:
            settings = await self.get_automod_settings(message.guild.id)
            if not settings:
                return None

            # スパム検出
            if settings.get('spam_protection'):
                if await self._check_spam(message):
                    return "スパム"

            # メンション数制限
            if settings.get('max_mentions'):
                if len(message.mentions) + len(message.role_mentions) > settings['max_mentions']:
                    return "メンション数制限超過"

            # 招待リンク制限
            if settings.get('block_invites'):
                if await self._check_invites(message):
                    return "招待リンク"

            # 外部リンク制限
            if settings.get('block_links'):
                if await self._check_links(message):
                    return "外部リンク"

            # 大文字制限
            if settings.get('caps_threshold'):
                if await self._check_caps(message, settings['caps_threshold']):
                    return "大文字の過剰使用"

            # 絵文字制限
            if settings.get('max_emojis'):
                if await self._check_emojis(message, settings['max_emojis']):
                    return "絵文字の過剰使用"

            # 禁止ワード
            if settings.get('banned_words'):
                if await self._check_banned_words(message, settings['banned_words']):
                    return "禁止ワード"

            return None

        except Exception as e:
            logger.error(f"Failed to check message: {e}")
            return None

    async def handle_violation(
        self,
        message: discord.Message,
        violation_type: str
    ) -> None:
        """
        違反を処理します。
        """
        try:
            settings = await self.get_automod_settings(message.guild.id)
            if not settings:
                return

            # メッセージを削除
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            # 警告を記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.add_warning(
                    user_id=message.author.id,
                    guild_id=message.guild.id,
                    moderator_id=self.bot.user.id,
                    reason=f"自動モデレーション: {violation_type}"
                )

                # 警告回数を取得
                warnings = await db.get_warnings(message.author.id, message.guild.id)
                warning_count = len(warnings)

            # 警告回数に応じたアクション
            if warning_count >= settings.get('max_warnings', 5):
                if settings.get('action') == 'kick':
                    try:
                        await message.author.kick(reason=f"警告回数超過 ({warning_count}回)")
                    except discord.Forbidden:
                        pass
                elif settings.get('action') == 'ban':
                    try:
                        await message.author.ban(reason=f"警告回数超過 ({warning_count}回)")
                    except discord.Forbidden:
                        pass
                elif settings.get('action') == 'timeout':
                    try:
                        duration = settings.get('timeout_duration', 3600)  # デフォルト1時間
                        until = discord.utils.utcnow() + timedelta(seconds=duration)
                        await message.author.timeout(until, reason=f"警告回数超過 ({warning_count}回)")
                    except discord.Forbidden:
                        pass

            # 違反をログに記録
            if settings.get('log_channel_id'):
                channel = message.guild.get_channel(settings['log_channel_id'])
                if channel:
                    embed = discord.Embed(
                        title="自動モデレーション",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="違反タイプ", value=violation_type, inline=False)
                    embed.add_field(name="ユーザー", value=f"{message.author} ({message.author.id})", inline=False)
                    embed.add_field(name="チャンネル", value=message.channel.mention, inline=False)
                    embed.add_field(name="メッセージ内容", value=message.content[:1024], inline=False)
                    embed.add_field(name="警告回数", value=warning_count, inline=False)
                    await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to handle violation: {e}")

    async def _check_spam(self, message: discord.Message) -> bool:
        """
        スパムをチェックします。
        """
        author_id = message.author.id
        channel_id = message.channel.id
        key = f"{author_id}-{channel_id}"
        now = datetime.utcnow()

        if key in self.spam_cooldowns:
            last_message, count = self.spam_cooldowns[key]
            if (now - last_message).total_seconds() < 5:  # 5秒以内
                if count >= 5:  # 5メッセージ以上
                    return True
                self.spam_cooldowns[key] = (now, count + 1)
            else:
                self.spam_cooldowns[key] = (now, 1)
        else:
            self.spam_cooldowns[key] = (now, 1)

        return False

    async def _check_invites(self, message: discord.Message) -> bool:
        """
        招待リンクをチェックします。
        """
        invite_pattern = r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+"
        return bool(re.search(invite_pattern, message.content))

    async def _check_links(self, message: discord.Message) -> bool:
        """
        外部リンクをチェックします。
        """
        link_pattern = r"(?:https?://)?(?:[\w-]+\.)+[\w-]+[/\w-]*"
        return bool(re.search(link_pattern, message.content))

    async def _check_caps(self, message: discord.Message, threshold: float) -> bool:
        """
        大文字の使用をチェックします。
        """
        if len(message.content) < 8:  # 短いメッセージは無視
            return False

        caps_count = sum(1 for c in message.content if c.isupper())
        caps_ratio = caps_count / len(message.content)
        return caps_ratio > threshold

    async def _check_emojis(self, message: discord.Message, max_emojis: int) -> bool:
        """
        絵文字の使用をチェックします。
        """
        emoji_pattern = r"<a?:\w+:\d+>|[\U0001F300-\U0001F9FF]"
        emojis = re.findall(emoji_pattern, message.content)
        return len(emojis) > max_emojis

    async def _check_banned_words(self, message: discord.Message, banned_words: List[str]) -> bool:
        """
        禁止ワードをチェックします。
        """
        content = message.content.lower()
        return any(word.lower() in content for word in banned_words) 