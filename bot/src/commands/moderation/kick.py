from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
from database.database_connection import get_db
from database.database_operations import DatabaseOperations
import logging

logger = logging.getLogger('moderation.kick')

class Kick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="指定したユーザーをKICKします")
    @app_commands.describe(
        member="KICKするユーザー",
        reason="KICKの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = "理由が指定されていません"
    ):
        """
        指定したユーザーをKICKします。
        
        Parameters
        ----------
        member : discord.Member
            KICKするユーザー
        reason : str, optional
            KICKの理由
        """
        # 権限チェック
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "自分より上位のロールを持つユーザーをKICKすることはできません。",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "BOTより上位のロールを持つユーザーをKICKすることはできません。",
                ephemeral=True
            )
            return

        try:
            # KICKを実行
            await member.kick(reason=f"{reason} (実行者: {interaction.user})")

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=interaction.guild.id,
                    action_type="kick",
                    user_id=interaction.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={}
                )

            # 成功メッセージを送信
            embed = discord.Embed(
                title="ユーザーをKICKしました",
                color=discord.Color.orange()
            )
            embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

            # ログチャンネルにも記録
            guild_data = await db.get_guild(interaction.guild.id)
            if guild_data and guild_data.log_channel_id:
                log_channel = interaction.guild.get_channel(guild_data.log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)

            # 対象ユーザーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} からKICKされました",
                    color=discord.Color.orange()
                )
                embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except discord.Forbidden:
            await interaction.response.send_message(
                "KICKの権限がありません。",
                ephemeral=True
            )
            logger.error(f"Failed to kick user {member.id} in guild {interaction.guild.id}: Forbidden")

        except Exception as e:
            await interaction.response.send_message(
                "KICKの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to kick user {member.id} in guild {interaction.guild.id}: {e}")

    @kick.error
    async def kick_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """KICKコマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "BOTにKICKの権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in kick command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Kick(bot)) 