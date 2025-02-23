from discord.ext import commands
import discord
import logging
from modules.moderation.raid_detection import RaidDetector
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('events.member')

class MemberEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.raid_detector = RaidDetector(bot)
        # クリーンアップタスクを開始
        self.bot.loop.create_task(self.raid_detector.start_cleanup_task())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        メンバーが参加したときのイベントハンドラ
        """
        try:
            # レイドチェック
            is_raid, detection_type, action = await self.raid_detector.check_member_join(member)
            
            if is_raid:
                # レイド対策アクションを実行
                await self.raid_detector.take_action(member, detection_type, action)
                
                # ログにも記録
                logger.warning(
                    f"Raid detected in guild {member.guild.id} "
                    f"by user {member.id}: {detection_type}"
                )
            else:
                # 通常の参加処理
                await self._handle_normal_join(member)

        except Exception as e:
            logger.error(f"Error in member join event handler: {e}")

    async def _handle_normal_join(self, member: discord.Member):
        """通常の参加処理を行います"""
        try:
            # ギルド設定を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(member.guild.id)

                if guild_data:
                    # ウェルカムメッセージを送信
                    if guild_data.welcome_channel_id and guild_data.welcome_message:
                        welcome_channel = member.guild.get_channel(guild_data.welcome_channel_id)
                        if welcome_channel:
                            # メッセージ内の変数を置換
                            message = guild_data.welcome_message.replace(
                                "{user}", member.mention
                            ).replace(
                                "{server}", member.guild.name
                            )
                            
                            await welcome_channel.send(message)

                    # 監査ログに記録
                    await db.create_audit_log(
                        guild_id=member.guild.id,
                        action_type="member_join",
                        user_id=member.id,
                        target_id=member.guild.id,
                        reason="メンバーが参加しました",
                        details={
                            "account_age": (discord.utils.utcnow() - member.created_at).days,
                            "name": str(member),
                            "id": member.id
                        }
                    )

        except Exception as e:
            logger.error(f"Error in normal join handler: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        メンバーが退出したときのイベントハンドラ
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(member.guild.id)

                if guild_data:
                    # 退出メッセージを送信
                    if guild_data.leave_message:
                        channel = member.guild.system_channel
                        if channel:
                            # メッセージ内の変数を置換
                            message = guild_data.leave_message.replace(
                                "{user}", str(member)
                            ).replace(
                                "{server}", member.guild.name
                            )
                            
                            await channel.send(message)

                    # 監査ログに記録
                    await db.create_audit_log(
                        guild_id=member.guild.id,
                        action_type="member_remove",
                        user_id=member.id,
                        target_id=member.guild.id,
                        reason="メンバーが退出しました",
                        details={
                            "name": str(member),
                            "id": member.id
                        }
                    )

        except Exception as e:
            logger.error(f"Error in member remove event handler: {e}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(MemberEvents(bot)) 