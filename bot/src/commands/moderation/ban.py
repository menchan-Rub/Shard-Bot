from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations
import logging

logger = logging.getLogger('moderation.ban')

class Ban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="指定したユーザーをBANします")
    @app_commands.describe(
        member="BANするユーザー",
        reason="BANの理由",
        delete_message_days="削除するメッセージの日数（0-7）"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = "理由が指定されていません",
        delete_message_days: Optional[int] = 1
    ):
        """
        指定したユーザーをBANします。
        
        Parameters
        ----------
        member : discord.Member
            BANするユーザー
        reason : str, optional
            BANの理由
        delete_message_days : int, optional
            削除するメッセージの日数（0-7）
        """
        # 権限チェック
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "自分より上位のロールを持つユーザーをBANすることはできません。",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "BOTより上位のロールを持つユーザーをBANすることはできません。",
                ephemeral=True
            )
            return

        # メッセージ削除日数の制限
        delete_message_days = max(0, min(delete_message_days, 7))

        try:
            # BANを実行
            await member.ban(
                reason=f"{reason} (実行者: {interaction.user})",
                delete_message_days=delete_message_days
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=interaction.guild.id,
                    action_type="ban",
                    user_id=interaction.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={
                        "delete_message_days": delete_message_days
                    }
                )

            # 成功メッセージを送信
            embed = discord.Embed(
                title="ユーザーをBANしました",
                color=discord.Color.red()
            )
            embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)
            embed.set_footer(text=f"メッセージ削除: {delete_message_days}日分")

            await interaction.response.send_message(embed=embed)

            # ログチャンネルにも記録
            guild_data = await db.get_guild(interaction.guild.id)
            if guild_data and guild_data.log_channel_id:
                log_channel = interaction.guild.get_channel(guild_data.log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "BANの権限がありません。",
                ephemeral=True
            )
            logger.error(f"Failed to ban user {member.id} in guild {interaction.guild.id}: Forbidden")

        except Exception as e:
            await interaction.response.send_message(
                "BANの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to ban user {member.id} in guild {interaction.guild.id}: {e}")

    @ban.error
    async def ban_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """BANコマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "BOTにBANの権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in ban command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Ban(bot)) 