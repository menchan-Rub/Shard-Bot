from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
from datetime import datetime, timedelta
import re
from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations
import logging

logger = logging.getLogger('moderation.mute')

class Mute(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="mute", description="指定したユーザーをミュートします")
    @app_commands.describe(
        member="ミュートするユーザー",
        duration="ミュート期間（例: 1h, 30m, 1d）",
        reason="ミュートの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[str] = "理由が指定されていません"
    ):
        """
        指定したユーザーをミュートします。
        
        Parameters
        ----------
        member : discord.Member
            ミュートするユーザー
        duration : str
            ミュート期間（例: 1h, 30m, 1d）
        reason : str, optional
            ミュートの理由
        """
        # 権限チェック
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "自分より上位のロールを持つユーザーをミュートすることはできません。",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "BOTより上位のロールを持つユーザーをミュートすることはできません。",
                ephemeral=True
            )
            return

        # 期間のパース
        try:
            duration_seconds = self._parse_duration(duration)
            if duration_seconds <= 0:
                await interaction.response.send_message(
                    "無効な期間が指定されました。",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "無効な期間形式です。例: 1h, 30m, 1d",
                ephemeral=True
            )
            return

        try:
            # ミュートロールを取得または作成
            mute_role = None
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(interaction.guild.id)
                
                if guild_data and guild_data.mute_role_id:
                    mute_role = interaction.guild.get_role(guild_data.mute_role_id)

            if not mute_role:
                # ミュートロールを作成
                mute_role = await self._create_mute_role(interaction.guild)
                # データベースに保存
                async for session in get_db():
                    db = DatabaseOperations(session)
                    await db.update_guild(
                        interaction.guild.id,
                        mute_role_id=mute_role.id
                    )

            # ミュートを実行
            await member.add_roles(
                mute_role,
                reason=f"{reason} (実行者: {interaction.user})"
            )

            # タイマーを設定
            unmute_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_timer(
                    guild_id=interaction.guild.id,
                    channel_id=interaction.channel.id,
                    user_id=member.id,
                    expires_at=unmute_time,
                    message=f"ミュート解除: {member.mention}",
                    is_recurring=False
                )

                # 監査ログに記録
                await db.create_audit_log(
                    guild_id=interaction.guild.id,
                    action_type="mute",
                    user_id=interaction.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={
                        "duration": duration,
                        "duration_seconds": duration_seconds,
                        "unmute_time": unmute_time.isoformat()
                    }
                )

            # 成功メッセージを送信
            embed = discord.Embed(
                title="ユーザーをミュートしました",
                color=discord.Color.orange()
            )
            embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="期間", value=duration, inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)
            embed.set_footer(text=f"解除予定: {unmute_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            await interaction.response.send_message(embed=embed)

            # ログチャンネルにも記録
            if guild_data and guild_data.log_channel_id:
                log_channel = interaction.guild.get_channel(guild_data.log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)

            # 対象ユーザーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} でミュートされました",
                    color=discord.Color.orange()
                )
                embed.add_field(name="期間", value=duration, inline=False)
                embed.add_field(name="理由", value=reason, inline=False)
                embed.set_footer(text=f"解除予定: {unmute_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except discord.Forbidden:
            await interaction.response.send_message(
                "ミュートの権限がありません。",
                ephemeral=True
            )
            logger.error(f"Failed to mute user {member.id} in guild {interaction.guild.id}: Forbidden")

        except Exception as e:
            await interaction.response.send_message(
                "ミュートの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to mute user {member.id} in guild {interaction.guild.id}: {e}")

    @app_commands.command(name="unmute", description="指定したユーザーのミュートを解除します")
    @app_commands.describe(
        member="ミュートを解除するユーザー",
        reason="解除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = "理由が指定されていません"
    ):
        """
        指定したユーザーのミュートを解除します。
        
        Parameters
        ----------
        member : discord.Member
            ミュートを解除するユーザー
        reason : str, optional
            解除の理由
        """
        try:
            # ミュートロールを取得
            mute_role = None
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(interaction.guild.id)
                
                if guild_data and guild_data.mute_role_id:
                    mute_role = interaction.guild.get_role(guild_data.mute_role_id)

            if not mute_role:
                await interaction.response.send_message(
                    "ミュートロールが設定されていません。",
                    ephemeral=True
                )
                return

            # ミュート解除を実行
            if mute_role in member.roles:
                await member.remove_roles(
                    mute_role,
                    reason=f"{reason} (実行者: {interaction.user})"
                )

                # 監査ログに記録
                async for session in get_db():
                    db = DatabaseOperations(session)
                    await db.create_audit_log(
                        guild_id=interaction.guild.id,
                        action_type="unmute",
                        user_id=interaction.user.id,
                        target_id=member.id,
                        reason=reason,
                        details={}
                    )

                # 成功メッセージを送信
                embed = discord.Embed(
                    title="ミュートを解除しました",
                    color=discord.Color.green()
                )
                embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
                embed.add_field(name="理由", value=reason, inline=False)
                embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

                await interaction.response.send_message(embed=embed)

                # ログチャンネルにも記録
                if guild_data and guild_data.log_channel_id:
                    log_channel = interaction.guild.get_channel(guild_data.log_channel_id)
                    if log_channel:
                        await log_channel.send(embed=embed)

                # 対象ユーザーにDMで通知
                try:
                    embed = discord.Embed(
                        title=f"{interaction.guild.name} でミュートが解除されました",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="理由", value=reason, inline=False)
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass  # DMが送れない場合は無視

            else:
                await interaction.response.send_message(
                    f"{member.mention} はミュートされていません。",
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "ミュート解除の権限がありません。",
                ephemeral=True
            )
            logger.error(f"Failed to unmute user {member.id} in guild {interaction.guild.id}: Forbidden")

        except Exception as e:
            await interaction.response.send_message(
                "ミュート解除の実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to unmute user {member.id} in guild {interaction.guild.id}: {e}")

    def _parse_duration(self, duration: str) -> int:
        """
        期間文字列を秒数に変換します
        
        Parameters
        ----------
        duration : str
            期間文字列（例: 1h, 30m, 1d）
            
        Returns
        -------
        int
            秒数
        """
        pattern = re.compile(r"^(\d+)([dhms])$")
        match = pattern.match(duration.lower())
        
        if not match:
            raise ValueError("Invalid duration format")
            
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit == "d":
            return value * 86400
        elif unit == "h":
            return value * 3600
        elif unit == "m":
            return value * 60
        else:  # s
            return value

    async def _create_mute_role(self, guild: discord.Guild) -> discord.Role:
        """
        ミュートロールを作成します
        
        Parameters
        ----------
        guild : discord.Guild
            対象のサーバー
            
        Returns
        -------
        discord.Role
            作成されたミュートロール
        """
        # ロールを作成
        mute_role = await guild.create_role(
            name="Muted",
            reason="ミュートシステム用のロール",
            color=discord.Color.darker_grey(),
            permissions=discord.Permissions.none()
        )

        # 全チャンネルの権限を設定
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                await channel.set_permissions(
                    mute_role,
                    send_messages=False,
                    speak=False,
                    stream=False,
                    add_reactions=False,
                    reason="ミュートロールの権限を設定"
                )

        return mute_role

    @mute.error
    @unmute.error
    async def mute_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """ミュートコマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "BOTにロールの管理権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in mute/unmute command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Mute(bot)) 