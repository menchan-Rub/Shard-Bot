from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, List
from ....database.database_connection import get_db
from ....database.database_operations import DatabaseOperations
import logging

logger = logging.getLogger('moderation.warn')

class Warn(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="warn", description="指定したユーザーに警告を付与します")
    @app_commands.describe(
        member="警告するユーザー",
        reason="警告の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        """
        指定したユーザーに警告を付与します。
        
        Parameters
        ----------
        member : discord.Member
            警告するユーザー
        reason : str
            警告の理由
        """
        # 権限チェック
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "自分より上位のロールを持つユーザーを警告することはできません。",
                ephemeral=True
            )
            return

        try:
            # 警告を追加
            async for session in get_db():
                db = DatabaseOperations(session)
                warning = await db.add_warning(
                    user_id=member.id,
                    guild_id=interaction.guild.id,
                    moderator_id=interaction.user.id,
                    reason=reason
                )

                # 警告回数を取得
                warnings = await db.get_warnings(member.id, interaction.guild.id)
                warning_count = len(warnings)

                # 成功メッセージを送信
                embed = discord.Embed(
                    title="警告を付与しました",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
                embed.add_field(name="理由", value=reason, inline=False)
                embed.add_field(name="実行者", value=interaction.user.mention, inline=False)
                embed.add_field(name="警告回数", value=f"{warning_count}回", inline=False)

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
                        title=f"{interaction.guild.name} で警告を受けました",
                        color=discord.Color.yellow()
                    )
                    embed.add_field(name="理由", value=reason, inline=False)
                    embed.add_field(name="警告回数", value=f"{warning_count}回", inline=False)
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass  # DMが送れない場合は無視

                # 警告回数に応じたアクション
                await self._handle_warning_threshold(interaction, member, warning_count)

        except Exception as e:
            await interaction.response.send_message(
                "警告の付与中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to warn user {member.id} in guild {interaction.guild.id}: {e}")

    @app_commands.command(name="warnings", description="指定したユーザーの警告履歴を表示します")
    @app_commands.describe(
        member="確認するユーザー"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        """
        指定したユーザーの警告履歴を表示します。
        
        Parameters
        ----------
        member : discord.Member
            確認するユーザー
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                warnings = await db.get_warnings(member.id, interaction.guild.id)

                if not warnings:
                    await interaction.response.send_message(
                        f"{member.mention} の警告履歴はありません。",
                        ephemeral=True
                    )
                    return

                # 警告履歴を表示
                embed = discord.Embed(
                    title=f"{member} の警告履歴",
                    color=discord.Color.yellow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="警告回数", value=f"{len(warnings)}回", inline=False)

                for i, warning in enumerate(warnings, 1):
                    moderator = interaction.guild.get_member(warning.moderator_id)
                    moderator_name = moderator.mention if moderator else "不明"
                    
                    embed.add_field(
                        name=f"警告 #{i}",
                        value=f"理由: {warning.reason}\n"
                              f"実行者: {moderator_name}\n"
                              f"日時: {warning.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                        inline=False
                    )

                await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "警告履歴の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get warnings for user {member.id} in guild {interaction.guild.id}: {e}")

    @app_commands.command(name="clearwarnings", description="指定したユーザーの警告をすべて削除します")
    @app_commands.describe(
        member="警告を削除するユーザー",
        reason="削除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        """
        指定したユーザーの警告をすべて削除します。
        
        Parameters
        ----------
        member : discord.Member
            警告を削除するユーザー
        reason : str
            削除の理由
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                # 警告を削除
                await session.execute(
                    f"DELETE FROM warnings WHERE user_id = {member.id} AND guild_id = {interaction.guild.id}"
                )
                await session.commit()

                # 監査ログに記録
                await db.create_audit_log(
                    guild_id=interaction.guild.id,
                    action_type="clear_warnings",
                    user_id=interaction.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={}
                )

                # 成功メッセージを送信
                embed = discord.Embed(
                    title="警告履歴を削除しました",
                    color=discord.Color.green()
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

        except Exception as e:
            await interaction.response.send_message(
                "警告の削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to clear warnings for user {member.id} in guild {interaction.guild.id}: {e}")

    async def _handle_warning_threshold(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        warning_count: int
    ):
        """
        警告回数に応じたアクションを実行します
        
        Parameters
        ----------
        interaction : discord.Interaction
            コマンドのインタラクション
        member : discord.Member
            対象ユーザー
        warning_count : int
            警告回数
        """
        # 警告回数に応じたアクション
        if warning_count >= 5:
            # 5回以上で自動BAN
            try:
                await member.ban(reason=f"警告回数が {warning_count} 回に達しました")
                await interaction.followup.send(
                    f"{member.mention} は警告回数が {warning_count} 回に達したため、自動的にBANされました。"
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    f"警告回数が {warning_count} 回に達しましたが、BANの権限がないため実行できませんでした。",
                    ephemeral=True
                )

        elif warning_count >= 3:
            # 3回以上で自動キック
            try:
                await member.kick(reason=f"警告回数が {warning_count} 回に達しました")
                await interaction.followup.send(
                    f"{member.mention} は警告回数が {warning_count} 回に達したため、自動的にKICKされました。"
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    f"警告回数が {warning_count} 回に達しましたが、KICKの権限がないため実行できませんでした。",
                    ephemeral=True
                )

    @warn.error
    @warnings.error
    @clearwarnings.error
    async def warn_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """警告コマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in warn command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Warn(bot)) 