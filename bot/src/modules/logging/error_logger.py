import discord
from discord.ext import commands
import traceback
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import platform

class ErrorLogger:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    async def get_error_channel(self, guild: Optional[discord.Guild] = None) -> Optional[discord.TextChannel]:
        """エラーログ用のチャンネルを取得"""
        try:
            if guild:
                # ギルド固有のエラーチャンネルを取得
                async with self.bot.db.acquire() as conn:
                    result = await conn.fetchval(
                        "SELECT error_log_channel_id FROM guilds WHERE id = $1",
                        guild.id
                    )
                    if result:
                        return self.bot.get_channel(result)
            
            # グローバルエラーチャンネルを取得（開発者用）
            return self.bot.get_channel(int(self.bot.config['error_log_channel_id']))
        except Exception:
            return None

    def create_error_embed(
        self,
        error: Exception,
        command: Optional[str] = None,
        guild: Optional[discord.Guild] = None,
        user: Optional[discord.User] = None
    ) -> discord.Embed:
        """エラー情報を含む埋め込みメッセージを作成"""
        
        # エラートレースバックの取得
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # 基本的なシステム情報
        system_info = (
            f"Python: {sys.version}\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Discord.py: {discord.__version__}"
        )
        
        # エラー発生時の詳細情報
        timestamp = datetime.utcnow()
        
        embed = discord.Embed(
            title="⚠️ エラーが発生しました",
            description=f"```py\n{str(error)}```",
            color=discord.Color.red(),
            timestamp=timestamp
        )
        
        # コマンド情報
        if command:
            embed.add_field(
                name="コマンド",
                value=f"```{command}```",
                inline=False
            )
        
        # エラー詳細
        if len(tb) > 1024:
            # 長すぎる場合は分割
            parts = [tb[i:i + 1024] for i in range(0, len(tb), 1024)]
            for i, part in enumerate(parts, 1):
                embed.add_field(
                    name=f"トレースバック ({i}/{len(parts)})",
                    value=f"```py\n{part}```",
                    inline=False
                )
        else:
            embed.add_field(
                name="トレースバック",
                value=f"```py\n{tb}```",
                inline=False
            )
        
        # 発生場所の情報
        location_info = []
        if guild:
            location_info.append(f"サーバー: {guild.name} (ID: {guild.id})")
        if user:
            location_info.append(f"ユーザー: {user} (ID: {user.id})")
        
        if location_info:
            embed.add_field(
                name="発生場所",
                value="\n".join(location_info),
                inline=False
            )
        
        # システム情報
        embed.add_field(
            name="システム情報",
            value=f"```\n{system_info}```",
            inline=False
        )
        
        return embed

    async def log_error(
        self,
        error: Exception,
        command: Optional[str] = None,
        guild: Optional[discord.Guild] = None,
        user: Optional[discord.User] = None
    ) -> None:
        """エラーをログチャンネルに送信"""
        try:
            channel = await self.get_error_channel(guild)
            if not channel:
                return
            
            embed = self.create_error_embed(error, command, guild, user)
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"エラーログの送信に失敗しました: {e}")
            traceback.print_exc() 