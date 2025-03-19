import discord
from discord.ext import commands
import time
import datetime

# psutilを使ってメモリ使用量を取得するための試み
try:
    import psutil
    psutil_imported = True
except ImportError:
    psutil_imported = False

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cogのロード時の時刻を記録
        self.start_time = time.time()

    @commands.command(name="status", help="Botのステータスを表示します")
    async def status(self, ctx: commands.Context):
        # 現在時刻とロード時刻との差でアップタイムを計算
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
        
        # Botが参加しているサーバー数
        total_guilds = len(self.bot.guilds) if self.bot.guilds is not None else 0
        
        # メモリ使用量の計測（psutilが利用可能な場合）
        if psutil_imported:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / (1024 * 1024)
            memory_str = f"{memory_usage:.2f} MB"
        else:
            memory_str = "N/A"
        
        embed = discord.Embed(title="Bot Status", color=0x00ff00)
        embed.add_field(name="Uptime", value=uptime_str, inline=False)
        embed.add_field(name="Guilds", value=str(total_guilds), inline=False)
        embed.add_field(name="Memory Usage", value=memory_str, inline=False)
        embed.set_footer(text="Implemented: Shard-Bot by Expert Bot Developer")
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Status(bot)) 