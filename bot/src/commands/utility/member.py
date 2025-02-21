from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
import logging
from ...modules.utility.member_service import MemberService

logger = logging.getLogger('utility.member')

class Member(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.member_service = MemberService(bot)

    @app_commands.command(name="memberinfo", description="メンバーの情報を表示します")
    @app_commands.describe(
        member="情報を表示するメンバー"
    )
    @app_commands.guild_only()
    async def memberinfo(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None
    ):
        """メンバーの情報を表示します"""
        try:
            # メンバーが指定されていない場合は実行者の情報を表示
            member = member or interaction.user

            # メンバー情報を取得
            info = await self.member_service.get_member_info(member)

            # 情報を表示
            embed = discord.Embed(
                title="メンバー情報",
                color=member.color
            )
            embed.set_thumbnail(url=info['avatar_url'])

            # 基本情報
            embed.add_field(name="名前", value=info['name'], inline=True)
            embed.add_field(name="ID", value=info['id'], inline=True)
            if info['nick']:
                embed.add_field(name="ニックネーム", value=info['nick'], inline=True)

            # 日時情報
            embed.add_field(
                name="アカウント作成日時",
                value=info['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                inline=True
            )
            embed.add_field(
                name="サーバー参加日時",
                value=info['joined_at'].strftime('%Y-%m-%d %H:%M:%S'),
                inline=True
            )

            # ロール情報
            if info['roles']:
                embed.add_field(
                    name="ロール",
                    value=", ".join(info['roles']),
                    inline=False
                )

            # 権限情報
            if info['guild_permissions']:
                embed.add_field(
                    name="権限",
                    value=", ".join(info['guild_permissions']),
                    inline=False
                )

            # ステータス情報
            status_str = f"ステータス: {info['status']}"
            if info['is_on_mobile']:
                status_str += " (モバイル)"
            if 'activity' in info:
                status_str += f"\nアクティビティ: {info['activity']['type']} {info['activity']['name']}"
            embed.add_field(name="ステータス情報", value=status_str, inline=False)

            # 警告情報
            embed.add_field(name="警告回数", value=info['warning_count'], inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "メンバー情報の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get member info: {e}")

    @app_commands.command(name="kick", description="メンバーをキックします")
    @app_commands.describe(
        member="キックするメンバー",
        reason="キックの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None
    ):
        """メンバーをキックします"""
        try:
            # 権限チェック
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "自分より上位のロールを持つメンバーをキックすることはできません。",
                    ephemeral=True
                )
                return

            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "BOTより上位のロールを持つメンバーをキックすることはできません。",
                    ephemeral=True
                )
                return

            # キックを実行
            result = await self.member_service.kick_member(
                member=member,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーをキックしました",
                color=discord.Color.orange()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} からキックされました",
                    color=discord.Color.orange()
                )
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "キックの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to kick member: {e}")

    @app_commands.command(name="ban", description="メンバーをBANします")
    @app_commands.describe(
        member="BANするメンバー",
        delete_message_days="削除するメッセージの日数（0-7）",
        reason="BANの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        delete_message_days: Optional[int] = 1,
        reason: Optional[str] = None
    ):
        """メンバーをBANします"""
        try:
            # 権限チェック
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "自分より上位のロールを持つメンバーをBANすることはできません。",
                    ephemeral=True
                )
                return

            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "BOTより上位のロールを持つメンバーをBANすることはできません。",
                    ephemeral=True
                )
                return

            # メッセージ削除日数の制限
            delete_message_days = max(0, min(delete_message_days, 7))

            # BANを実行
            result = await self.member_service.ban_member(
                member=member,
                delete_message_days=delete_message_days,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーをBANしました",
                color=discord.Color.red()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)
            embed.set_footer(text=f"メッセージ削除: {delete_message_days}日分")

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} からBANされました",
                    color=discord.Color.red()
                )
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "BANの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to ban member: {e}")

    @app_commands.command(name="unban", description="メンバーのBANを解除します")
    @app_commands.describe(
        user_id="BAN解除するユーザーのID",
        reason="解除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: Optional[str] = None
    ):
        """メンバーのBANを解除します"""
        try:
            # ユーザーIDを解析
            try:
                user_id = int(user_id)
            except ValueError:
                await interaction.response.send_message(
                    "無効なユーザーIDです。",
                    ephemeral=True
                )
                return

            # BAN解除を実行
            result = await self.member_service.unban_member(
                guild=interaction.guild,
                user_id=user_id,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーのBANを解除しました",
                color=discord.Color.green()
            )
            embed.add_field(name="対象ユーザーID", value=user_id, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "BAN解除の実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to unban member: {e}")

    @app_commands.command(name="timeout", description="メンバーをタイムアウトします")
    @app_commands.describe(
        member="タイムアウトするメンバー",
        duration="タイムアウト期間（例: 1h, 30m, 1d）",
        reason="タイムアウトの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[str] = None
    ):
        """メンバーをタイムアウトします"""
        try:
            # 権限チェック
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message(
                    "自分より上位のロールを持つメンバーをタイムアウトすることはできません。",
                    ephemeral=True
                )
                return

            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "BOTより上位のロールを持つメンバーをタイムアウトすることはできません。",
                    ephemeral=True
                )
                return

            # 期間を解析
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

            # タイムアウトを実行
            result = await self.member_service.timeout_member(
                member=member,
                duration=duration_seconds,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーをタイムアウトしました",
                color=discord.Color.orange()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="期間", value=duration, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} でタイムアウトされました",
                    color=discord.Color.orange()
                )
                embed.add_field(name="期間", value=duration, inline=False)
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "タイムアウトの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to timeout member: {e}")

    @app_commands.command(name="untimeout", description="メンバーのタイムアウトを解除します")
    @app_commands.describe(
        member="タイムアウトを解除するメンバー",
        reason="解除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None
    ):
        """メンバーのタイムアウトを解除します"""
        try:
            # タイムアウト解除を実行
            result = await self.member_service.remove_timeout(
                member=member,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーのタイムアウトを解除しました",
                color=discord.Color.green()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} でタイムアウトが解除されました",
                    color=discord.Color.green()
                )
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "タイムアウト解除の実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to remove timeout: {e}")

    @app_commands.command(name="warn", description="メンバーに警告を付与します")
    @app_commands.describe(
        member="警告するメンバー",
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
        """メンバーに警告を付与します"""
        try:
            # 警告を付与
            result, warning_count = await self.member_service.warn_member(
                member=member,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーに警告を付与しました",
                color=discord.Color.yellow()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)
            embed.add_field(name="警告回数", value=warning_count, inline=False)

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} で警告を受けました",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="理由", value=reason, inline=False)
                embed.add_field(name="警告回数", value=warning_count, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "警告の付与中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to warn member: {e}")

    @app_commands.command(name="warnings", description="メンバーの警告履歴を表示します")
    @app_commands.describe(
        member="確認するメンバー"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        """メンバーの警告履歴を表示します"""
        try:
            # 警告履歴を取得
            warnings = await self.member_service.get_warnings(member)

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

            for warning in warnings:
                embed.add_field(
                    name=f"警告 #{warning['id']}",
                    value=f"理由: {warning['reason']}\n"
                          f"実行者: {warning['moderator']}\n"
                          f"日時: {warning['created_at'].strftime('%Y-%m-%d %H:%M:%S')}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "警告履歴の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get warnings: {e}")

    @app_commands.command(name="clearwarnings", description="メンバーの警告をすべて削除します")
    @app_commands.describe(
        member="警告を削除するメンバー",
        reason="削除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None
    ):
        """メンバーの警告をすべて削除します"""
        try:
            # 警告を削除
            result = await self.member_service.clear_warnings(
                member=member,
                reason=reason,
                moderator=interaction.user
            )

            # 結果を表示
            embed = discord.Embed(
                title="メンバーの警告をすべて削除しました",
                color=discord.Color.green()
            )
            embed.add_field(name="対象メンバー", value=f"{member} ({member.id})", inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="実行者", value=interaction.user.mention, inline=False)

            await interaction.response.send_message(embed=embed)

            # 対象メンバーにDMで通知
            try:
                embed = discord.Embed(
                    title=f"{interaction.guild.name} で警告がすべて削除されました",
                    color=discord.Color.green()
                )
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # DMが送れない場合は無視

        except Exception as e:
            await interaction.response.send_message(
                "警告の削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to clear warnings: {e}")

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
        import re
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

    @memberinfo.error
    @kick.error
    @ban.error
    @unban.error
    @timeout.error
    @untimeout.error
    @warn.error
    @warnings.error
    @clearwarnings.error
    async def member_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """メンバー管理コマンドのエラーハンドリング"""
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
            logger.error(f"Error in member command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Member(bot)) 