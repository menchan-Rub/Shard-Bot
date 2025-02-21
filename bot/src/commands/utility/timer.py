from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
from datetime import datetime, timedelta
import re
from ...modules.utility.timer_service import TimerService
import logging

logger = logging.getLogger('utility.timer')

class Timer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timer_service = TimerService(bot)
        # タイマーサービスを開始
        self.bot.loop.create_task(self.timer_service.start())

    def cog_unload(self):
        """Cogがアンロードされるときの処理"""
        # タイマーサービスを停止
        self.bot.loop.create_task(self.timer_service.stop())

    @app_commands.command(name="timer", description="タイマーを設定します")
    @app_commands.describe(
        duration="タイマーの時間（例: 1h, 30m, 1d）",
        message="タイマー終了時のメッセージ",
        recurring="繰り返し実行するかどうか"
    )
    @app_commands.guild_only()
    async def timer(
        self,
        interaction: discord.Interaction,
        duration: str,
        message: Optional[str] = None,
        recurring: Optional[bool] = False
    ):
        """
        タイマーを設定します。
        
        Parameters
        ----------
        duration : str
            タイマーの時間（例: 1h, 30m, 1d）
        message : str, optional
            タイマー終了時のメッセージ
        recurring : bool, optional
            繰り返し実行するかどうか
        """
        try:
            # 期間のパース
            duration_seconds = self._parse_duration(duration)
            if duration_seconds <= 0:
                await interaction.response.send_message(
                    "無効な期間が指定されました。",
                    ephemeral=True
                )
                return

            # 期限を計算
            expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)

            # デフォルトメッセージ
            if not message:
                message = f"{interaction.user.mention} タイマーが終了しました！"

            # タイマーを作成
            await self.timer_service.create_timer(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                user_id=interaction.user.id,
                expires_at=expires_at,
                message=message,
                is_recurring=recurring,
                interval=duration_seconds if recurring else None
            )

            # 成功メッセージを送信
            embed = discord.Embed(
                title="タイマーを設定しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="期間", value=duration, inline=False)
            embed.add_field(name="メッセージ", value=message, inline=False)
            if recurring:
                embed.add_field(name="繰り返し", value="有効", inline=False)
            embed.set_footer(text=f"終了予定: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"無効な期間形式です: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "タイマーの設定中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error setting timer: {e}")

    @app_commands.command(name="timers", description="設定中のタイマー一覧を表示します")
    @app_commands.guild_only()
    async def timers(
        self,
        interaction: discord.Interaction
    ):
        """設定中のタイマー一覧を表示します"""
        try:
            # タイマー一覧を取得
            timers = await self.timer_service.get_user_timers(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id
            )

            if not timers:
                await interaction.response.send_message(
                    "設定中のタイマーはありません。",
                    ephemeral=True
                )
                return

            # タイマー一覧を表示
            embed = discord.Embed(
                title="タイマー一覧",
                color=discord.Color.blue()
            )

            for timer in timers:
                remaining = timer.expires_at - datetime.utcnow()
                remaining_str = self._format_timedelta(remaining)
                
                value = f"残り時間: {remaining_str}\n"
                value += f"メッセージ: {timer.message}\n"
                if timer.is_recurring:
                    value += f"繰り返し: 有効（{self._format_seconds(timer.interval)}ごと）"

                embed.add_field(
                    name=f"タイマー #{timer.id}",
                    value=value,
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "タイマー一覧の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error getting timers: {e}")

    @app_commands.command(name="canceltimer", description="タイマーをキャンセルします")
    @app_commands.describe(
        timer_id="キャンセルするタイマーのID"
    )
    @app_commands.guild_only()
    async def canceltimer(
        self,
        interaction: discord.Interaction,
        timer_id: int
    ):
        """
        タイマーをキャンセルします。
        
        Parameters
        ----------
        timer_id : int
            キャンセルするタイマーのID
        """
        try:
            # タイマーをキャンセル
            await self.timer_service.cancel_timer(timer_id)

            await interaction.response.send_message(
                f"タイマー #{timer_id} をキャンセルしました。",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                "タイマーのキャンセル中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error cancelling timer: {e}")

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

    def _format_seconds(self, seconds: int) -> str:
        """
        秒数を読みやすい形式に変換します
        
        Parameters
        ----------
        seconds : int
            秒数
            
        Returns
        -------
        str
            フォーマットされた文字列
        """
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}日")
        if hours > 0:
            parts.append(f"{hours}時間")
        if minutes > 0:
            parts.append(f"{minutes}分")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}秒")

        return "".join(parts)

    def _format_timedelta(self, td: timedelta) -> str:
        """
        timedeltaを読みやすい形式に変換します
        
        Parameters
        ----------
        td : timedelta
            変換する時間差
            
        Returns
        -------
        str
            フォーマットされた文字列
        """
        return self._format_seconds(int(td.total_seconds()))

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Timer(bot)) 