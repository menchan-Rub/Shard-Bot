from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
import logging
from modules.utility.member_service import MemberService

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

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "メンバー情報の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get member info: {e}")

    @memberinfo.error
    async def member_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """メンバーコマンドのエラーハンドリング"""
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