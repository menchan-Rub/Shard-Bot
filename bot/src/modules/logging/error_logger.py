import discord
from discord.ext import commands
import traceback
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime
import platform
import io
import os
import json
import asyncio
from collections import defaultdict, Counter

class ErrorLogger:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.error_history = defaultdict(list)  # エラー履歴の追跡用
        self.error_counter = Counter()  # エラータイプのカウント
        self.error_limit = 10  # エラー通知の閾値
        self.error_cooldown = 3600  # エラー通知クールダウン（秒）
        self.last_notification = {}  # 最後の通知時間
        
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
            error_channel_id = getattr(self.bot, 'error_channel_id', None)
            if error_channel_id:
                return self.bot.get_channel(error_channel_id)
                
            # configから取得を試みる
            try:
                from config import get_config
                config = get_config()
                error_channel_id = config.get('bot', {}).get('error_log_channel_id')
                if error_channel_id:
                    return self.bot.get_channel(int(error_channel_id))
            except:
                pass
                
            return None
        except Exception:
            return None
            
    async def get_admin_users(self) -> List[discord.User]:
        """管理者ユーザーのリストを取得"""
        admin_users = []
        try:
            from config import get_config
            config = get_config()
            owner_ids = config.get('bot', {}).get('owner_ids', [])
            
            for owner_id in owner_ids:
                try:
                    user = await self.bot.fetch_user(owner_id)
                    if user:
                        admin_users.append(user)
                except:
                    pass
        except:
            pass
            
        return admin_users

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
            f"Discord.py: {discord.__version__}\n"
            f"Memory: {self.get_memory_usage()}"
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
        
        # エラー頻度
        error_type = type(error).__name__
        error_count = self.error_counter[error_type]
        embed.add_field(
            name="エラー統計",
            value=f"このタイプのエラー発生回数: {error_count}回",
            inline=False
        )
        
        return embed
        
    def get_memory_usage(self) -> str:
        """現在のメモリ使用量を取得"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return f"{memory_info.rss / 1024 / 1024:.2f} MB"
        except:
            return "不明"

    async def log_error(
        self,
        error: Exception,
        command: Optional[str] = None,
        guild: Optional[discord.Guild] = None,
        user: Optional[discord.User] = None
    ) -> None:
        """エラーをログチャンネルに送信し、必要に応じて通知"""
        try:
            # エラー統計の更新
            error_type = type(error).__name__
            self.error_counter[error_type] += 1
            
            # エラー履歴の更新
            error_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'error_type': error_type,
                'error_msg': str(error),
                'command': command,
                'guild_id': guild.id if guild else None,
                'guild_name': guild.name if guild else None,
                'user_id': user.id if user else None,
                'user_name': str(user) if user else None
            }
            self.error_history[error_type].append(error_info)
            
            # エラーログチャンネルに送信
            channel = await self.get_error_channel(guild)
            if channel:
                embed = self.create_error_embed(error, command, guild, user)
                await channel.send(embed=embed)
                
                # エラーの詳細が長い場合はファイルとしても送信
                tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                if len(tb) > 2000:
                    file_content = (
                        f"Error: {error_type}\n"
                        f"Message: {str(error)}\n"
                        f"Command: {command}\n"
                        f"Guild: {guild.name if guild else 'N/A'} (ID: {guild.id if guild else 'N/A'})\n"
                        f"User: {str(user) if user else 'N/A'} (ID: {user.id if user else 'N/A'})\n"
                        f"Timestamp: {datetime.utcnow().isoformat()}\n\n"
                        f"Traceback:\n{tb}"
                    )
                    file = discord.File(
                        io.StringIO(file_content),
                        filename=f"error_{error_type}_{int(datetime.utcnow().timestamp())}.txt"
                    )
                    await channel.send(file=file)
            
            # 重大なエラーが頻発している場合は管理者に通知
            await self.notify_admins_if_needed(error_type, error)
            
            # エラー履歴を定期的に保存
            await self.save_error_history()
            
        except Exception as e:
            print(f"エラーログの送信に失敗しました: {e}")
            traceback.print_exc()
            
    async def notify_admins_if_needed(self, error_type: str, error: Exception) -> None:
        """重大なエラーが頻発している場合に管理者に通知"""
        try:
            # エラーの閾値を超えているか確認
            if self.error_counter[error_type] < self.error_limit:
                return
                
            # クールダウン期間中なら通知しない
            now = datetime.utcnow().timestamp()
            if error_type in self.last_notification and now - self.last_notification[error_type] < self.error_cooldown:
                return
                
            # 管理者に通知
            admin_users = await self.get_admin_users()
            for admin in admin_users:
                try:
                    embed = discord.Embed(
                        title="🚨 重大なエラーが頻発しています",
                        description=f"エラータイプ `{error_type}` が閾値（{self.error_limit}回）を超えて発生しています。",
                        color=discord.Color.dark_red()
                    )
                    embed.add_field(
                        name="エラーメッセージ",
                        value=f"```{str(error)}```",
                        inline=False
                    )
                    embed.add_field(
                        name="発生回数",
                        value=f"{self.error_counter[error_type]}回",
                        inline=True
                    )
                    embed.add_field(
                        name="最終発生",
                        value=f"<t:{int(now)}:R>",
                        inline=True
                    )
                    await admin.send(embed=embed)
                except:
                    pass
                    
            # 最後の通知時間を更新
            self.last_notification[error_type] = now
        except:
            pass
            
    async def save_error_history(self) -> None:
        """エラー履歴をJSONファイルに保存"""
        try:
            # 保存先ディレクトリの確認
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # エラー履歴をJSONに変換
            error_data = {
                'last_updated': datetime.utcnow().isoformat(),
                'error_counts': dict(self.error_counter),
                'error_history': {k: v[-100:] for k, v in self.error_history.items()}  # 各タイプの最新100件のみ保存
            }
            
            # ファイルに保存
            filename = os.path.join(logs_dir, 'error_history.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    async def analyze_errors(self) -> discord.Embed:
        """エラー分析レポートを生成"""
        embed = discord.Embed(
            title="📊 エラー分析レポート",
            description="直近のエラー統計と分析",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # エラータイプ別の発生回数
        top_errors = self.error_counter.most_common(5)
        if top_errors:
            error_stats = "\n".join([f"{error_type}: {count}回" for error_type, count in top_errors])
            embed.add_field(
                name="最も多いエラー（上位5件）",
                value=f"```{error_stats}```",
                inline=False
            )
        else:
            embed.add_field(
                name="最も多いエラー",
                value="エラーは記録されていません",
                inline=False
            )
            
        # 全体のエラー数
        total_errors = sum(self.error_counter.values())
        embed.add_field(
            name="総エラー数",
            value=f"{total_errors}回",
            inline=True
        )
        
        # エラータイプの数
        embed.add_field(
            name="エラータイプ数",
            value=f"{len(self.error_counter)}種類",
            inline=True
        )
        
        return embed 