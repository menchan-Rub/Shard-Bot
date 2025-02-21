from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, List
import re
from datetime import timedelta
import logging
from ...modules.utility.poll_service import PollService

logger = logging.getLogger('utility.poll')

class Poll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.poll_service = PollService(bot)

    @app_commands.command(name="poll", description="投票を作成します")
    @app_commands.describe(
        title="投票のタイトル",
        options="選択肢（カンマ区切り、最大10個）",
        duration="投票の期間（例: 1h, 30m, 1d）",
        multiple_choice="複数選択を許可するかどうか"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        title: str,
        options: Optional[str] = None,
        duration: Optional[str] = None,
        multiple_choice: Optional[bool] = False
    ):
        """
        投票を作成します。
        
        Parameters
        ----------
        title : str
            投票のタイトル
        options : str, optional
            選択肢（カンマ区切り）
        duration : str, optional
            投票の期間（例: 1h, 30m, 1d）
        multiple_choice : bool, optional
            複数選択を許可するかどうか
        """
        await interaction.response.defer()

        try:
            # 選択肢を解析
            option_list = None
            if options:
                option_list = [
                    opt.strip()
                    for opt in options.split(',')
                    if opt.strip()
                ]
                if len(option_list) > 10:
                    await interaction.followup.send(
                        "選択肢は最大10個までです。",
                        ephemeral=True
                    )
                    return
                if len(option_list) < 2:
                    await interaction.followup.send(
                        "選択肢は2つ以上指定してください。",
                        ephemeral=True
                    )
                    return

            # 期間を解析
            duration_seconds = None
            if duration:
                try:
                    duration_seconds = self._parse_duration(duration)
                    if duration_seconds <= 0:
                        await interaction.followup.send(
                            "無効な期間が指定されました。",
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.followup.send(
                        "無効な期間形式です。例: 1h, 30m, 1d",
                        ephemeral=True
                    )
                    return

            # 投票を作成
            message = await self.poll_service.create_poll(
                channel=interaction.channel,
                author=interaction.user,
                title=title,
                options=option_list,
                duration=duration_seconds,
                multiple_choice=multiple_choice
            )

            if not message:
                await interaction.followup.send(
                    "投票の作成に失敗しました。",
                    ephemeral=True
                )
                return

            # 成功メッセージを送信
            await interaction.followup.send(
                "投票を作成しました。",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.followup.send(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                "投票の作成中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to create poll: {e}")

    @app_commands.command(name="endpoll", description="投票を終了します")
    @app_commands.describe(
        message_id="終了する投票のメッセージID"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def endpoll(
        self,
        interaction: discord.Interaction,
        message_id: str
    ):
        """
        投票を終了します。
        
        Parameters
        ----------
        message_id : str
            終了する投票のメッセージID
        """
        try:
            # メッセージIDを解析
            try:
                message_id = int(message_id)
            except ValueError:
                await interaction.response.send_message(
                    "無効なメッセージIDです。",
                    ephemeral=True
                )
                return

            # メッセージを取得
            try:
                message = await interaction.channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "指定されたメッセージが見つかりません。",
                    ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "メッセージの取得権限がありません。",
                    ephemeral=True
                )
                return

            # 投票を終了
            await self.poll_service.end_poll(message)
            await interaction.response.send_message(
                "投票を終了しました。",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                "投票の終了中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to end poll: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """リアクションが追加されたときの処理"""
        if payload.user_id == self.bot.user.id:
            return

        try:
            # 投票を処理
            if await self.poll_service.handle_vote(
                message_id=payload.message_id,
                user_id=payload.user_id,
                emoji=str(payload.emoji)
            ):
                # メッセージを更新
                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    message = await channel.fetch_message(payload.message_id)
                    await self.poll_service.update_poll_message(message)

        except Exception as e:
            logger.error(f"Failed to handle reaction add: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """リアクションが削除されたときの処理"""
        if payload.user_id == self.bot.user.id:
            return

        try:
            # 投票を取り消し
            if await self.poll_service.remove_vote(
                message_id=payload.message_id,
                user_id=payload.user_id,
                emoji=str(payload.emoji)
            ):
                # メッセージを更新
                channel = self.bot.get_channel(payload.channel_id)
                if channel:
                    message = await channel.fetch_message(payload.message_id)
                    await self.poll_service.update_poll_message(message)

        except Exception as e:
            logger.error(f"Failed to handle reaction remove: {e}")

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

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Poll(bot)) 