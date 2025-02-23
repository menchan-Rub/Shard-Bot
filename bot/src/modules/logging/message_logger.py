import discord
from discord.ext import commands
import logging
import io
from typing import List, Dict, Any, Optional
from datetime import datetime

from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('modules.logging.message_logger')

class MessageLogger:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """ログチャンネルを取得または作成"""
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(guild.id)
                
                if guild_data and guild_data.log_channel_id:
                    channel = guild.get_channel(guild_data.log_channel_id)
                    if channel:
                        return channel
                        
            # ログチャンネルが見つからない場合は作成
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            channel = await guild.create_text_channel(
                'mod-logs',
                overwrites=overwrites,
                reason="Automatic log channel creation"
            )
            
            # データベースに保存
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.update_guild(guild.id, log_channel_id=channel.id)
                
            return channel
            
        except Exception as e:
            logger.error(f"Error getting log channel: {e}")
            return None

    def create_embed(
        self,
        title: str,
        description: str,
        color: discord.Color,
        fields: List[Dict[str, Any]] = None
    ) -> discord.Embed:
        """Embedを作成"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field['name'],
                    value=field['value'],
                    inline=field.get('inline', False)
                )
                
        return embed

    async def log_message(self, message: discord.Message):
        """メッセージを記録"""
        try:
            if not message.guild:
                return
                
            log_channel = await self.get_log_channel(message.guild)
            if not log_channel:
                return
                
            # 添付ファイルの情報を取得
            attachments = []
            for attachment in message.attachments:
                attachments.append(f"[{attachment.filename}]({attachment.url})")
                
            # Embedを作成
            embed = self.create_embed(
                title="メッセージ送信",
                description=message.content or "（本文なし）",
                color=discord.Color.green(),
                fields=[
                    {
                        'name': "送信者",
                        'value': f"{message.author} ({message.author.id})",
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{message.channel.mention} ({message.channel.id})",
                        'inline': True
                    }
                ]
            )
            
            if attachments:
                embed.add_field(
                    name="添付ファイル",
                    value="\n".join(attachments),
                    inline=False
                )
                
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging message: {e}")

    async def log_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集を記録"""
        try:
            if not after.guild:
                return
                
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return
                
            # 内容が変更されていない場合は無視
            if before.content == after.content:
                return
                
            # Embedを作成
            embed = self.create_embed(
                title="メッセージ編集",
                description="",
                color=discord.Color.blue(),
                fields=[
                    {
                        'name': "送信者",
                        'value': f"{after.author} ({after.author.id})",
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{after.channel.mention} ({after.channel.id})",
                        'inline': True
                    },
                    {
                        'name': "編集前",
                        'value': before.content or "（本文なし）",
                        'inline': False
                    },
                    {
                        'name': "編集後",
                        'value': after.content or "（本文なし）",
                        'inline': False
                    }
                ]
            )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging message edit: {e}")

    async def log_message_delete(self, message: discord.Message):
        """メッセージ削除を記録"""
        try:
            if not message.guild:
                return
                
            log_channel = await self.get_log_channel(message.guild)
            if not log_channel:
                return
                
            # 添付ファイルの情報を取得
            attachments = []
            for attachment in message.attachments:
                attachments.append(f"[{attachment.filename}]({attachment.url})")
                
            # Embedを作成
            embed = self.create_embed(
                title="メッセージ削除",
                description=message.content or "（本文なし）",
                color=discord.Color.red(),
                fields=[
                    {
                        'name': "送信者",
                        'value': f"{message.author} ({message.author.id})",
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{message.channel.mention} ({message.channel.id})",
                        'inline': True
                    }
                ]
            )
            
            if attachments:
                embed.add_field(
                    name="添付ファイル",
                    value="\n".join(attachments),
                    inline=False
                )
                
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging message delete: {e}")

    async def log_bulk_message_delete(self, messages: List[discord.Message]):
        """メッセージの一括削除を記録"""
        try:
            if not messages:
                return
                
            guild = messages[0].guild
            if not guild:
                return
                
            log_channel = await self.get_log_channel(guild)
            if not log_channel:
                return
                
            # 削除されたメッセージの内容をファイルに出力
            content = []
            for message in sorted(messages, key=lambda m: m.created_at):
                content.append(
                    f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{message.author} ({message.author.id}): {message.content}"
                )
                
                if message.attachments:
                    for attachment in message.attachments:
                        content.append(f"  添付ファイル: {attachment.filename} ({attachment.url})")
                        
            file = discord.File(
                io.StringIO("\n".join(content)),
                filename="deleted_messages.txt"
            )
            
            # Embedを作成
            embed = self.create_embed(
                title="メッセージ一括削除",
                description=f"{len(messages)}件のメッセージが削除されました",
                color=discord.Color.red(),
                fields=[
                    {
                        'name': "チャンネル",
                        'value': f"{messages[0].channel.mention} ({messages[0].channel.id})",
                        'inline': True
                    }
                ]
            )
            
            await log_channel.send(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error logging bulk message delete: {e}") 