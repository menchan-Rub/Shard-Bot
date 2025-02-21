from discord.ext import commands
import discord
import logging
from ..modules.utility.automod_service import AutoModService

logger = logging.getLogger('events.message')

class MessageHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.automod_service = AutoModService(bot)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージイベントのハンドリング"""
        # BOTのメッセージは無視
        if message.author.bot:
            return

        # DMは無視
        if not message.guild:
            return

        try:
            # 自動モデレーションチェック
            violation = await self.automod_service.check_message(message)
            if violation:
                await self.automod_service.handle_violation(message, violation)

        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集イベントのハンドリング"""
        # BOTのメッセージは無視
        if after.author.bot:
            return

        # DMは無視
        if not after.guild:
            return

        # 内容が変更されていない場合は無視
        if before.content == after.content:
            return

        try:
            # 自動モデレーションチェック
            violation = await self.automod_service.check_message(after)
            if violation:
                await self.automod_service.handle_violation(after, violation)

        except Exception as e:
            logger.error(f"Error in message edit handler: {e}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(MessageHandler(bot)) 