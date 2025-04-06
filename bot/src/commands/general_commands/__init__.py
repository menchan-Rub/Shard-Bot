import discord
from discord import app_commands
from discord.ext import commands

class GeneralCommands(commands.Cog):
    """一般的なコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """ボットの応答速度を確認します"""
        latency = self.bot.latency * 1000
        await ctx.send(f"🏓 Pong! レイテンシ: {latency:.2f}ms")
    
    @commands.command(name="hello")
    async def hello(self, ctx):
        """挨拶します"""
        await ctx.send(f"こんにちは、{ctx.author.mention}さん！")
    
    @app_commands.command(name="help", description="ヘルプを表示します")
    async def help_slash(self, interaction: discord.Interaction):
        """ヘルプコマンド(スラッシュ)"""
        embed = discord.Embed(
            title="Shard Bot ヘルプ",
            description="利用可能なコマンドの一覧です",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="一般コマンド",
            value="• `!ping` - ボットの応答速度を確認\n"
                 "• `!hello` - ボットからの挨拶\n"
                 "• `/help` - このヘルプを表示",
            inline=False
        )
        
        embed.add_field(
            name="自動応答コマンド",
            value="• `/auto-response` - 自動応答システムの設定を管理\n"
                 "• `/auto-response-test` - 自動応答のテスト",
            inline=False
        )
        
        embed.set_footer(text="詳細な設定はWebダッシュボードから行えます")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """コマンド拡張のセットアップ関数"""
    await bot.add_cog(GeneralCommands(bot)) 