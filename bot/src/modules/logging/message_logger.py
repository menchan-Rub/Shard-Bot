import discord
from discord.ext import commands
import logging
import io
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import json
import os
import asyncio
import re
from collections import defaultdict
import random

from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('modules.logging.message_logger')

class MessageLogger:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_cache = defaultdict(list)  # メッセージキャッシュ {guild_id: [messages]}
        self.max_cache_size = 1000  # ギルドごとの最大キャッシュサイズ
        self.message_history = {}  # 検索可能なメッセージ履歴
        
        # ログファイルパス
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        self.log_file_path = os.path.join(logs_dir, 'message_logs.json')
        
        # 設定を読み込む
        try:
            from config import get_config
            config = get_config()
            log_config = config.get('logging', {})
            self.log_retention_days = log_config.get('log_retention_days', 30)
            self.separate_log_files = log_config.get('separate_log_files', True)
            self.rich_embed_logs = log_config.get('rich_embed_logs', True)
            self.log_user_ids = log_config.get('log_user_ids', True)
            self.enabled_events = log_config.get('enabled_events', [])
        except:
            self.log_retention_days = 30
            self.separate_log_files = True
            self.rich_embed_logs = True
            self.log_user_ids = True
            self.enabled_events = [
                'message_delete', 'message_edit', 'member_join', 'member_remove',
                'member_ban', 'member_unban', 'role_create', 'role_delete',
                'channel_create', 'channel_delete'
            ]
        
        # バックグラウンドタスクを開始
        self.bot.loop.create_task(self.load_message_history())
        self.bot.loop.create_task(self.periodic_cleanup())

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
            
    async def get_log_file_path(self, guild_id: int, event_type: str) -> str:
        """ログファイルのパスを取得"""
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        guild_logs_dir = os.path.join(logs_dir, str(guild_id))
        
        if self.separate_log_files:
            os.makedirs(guild_logs_dir, exist_ok=True)
            return os.path.join(guild_logs_dir, f"{event_type}.json")
        else:
            os.makedirs(logs_dir, exist_ok=True)
            return os.path.join(logs_dir, f"{guild_id}_logs.json")

    def create_embed(
        self,
        title: str,
        description: str,
        color: discord.Color,
        fields: List[Dict[str, Any]] = None,
        footer: str = None,
        thumbnail: str = None
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
                
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
                
        return embed
        
    async def add_to_cache(self, message: discord.Message) -> None:
        """メッセージをキャッシュに追加"""
        if not message.guild:
            return
            
        # メッセージデータを保存
        message_data = {
            'id': message.id,
            'author_id': message.author.id,
            'author_name': str(message.author),
            'channel_id': message.channel.id,
            'channel_name': message.channel.name,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'attachments': [{'url': a.url, 'filename': a.filename} for a in message.attachments],
            'embeds': [e.to_dict() for e in message.embeds],
            'mentions': [user.id for user in message.mentions],
            'reference': message.reference.message_id if message.reference else None
        }
        
        # キャッシュに追加
        self.message_cache[message.guild.id].append(message_data)
        
        # キャッシュサイズを制限
        if len(self.message_cache[message.guild.id]) > self.max_cache_size:
            self.message_cache[message.guild.id].pop(0)  # 最も古いメッセージを削除
            
        # メッセージ履歴に追加
        if message.guild.id not in self.message_history:
            self.message_history[message.guild.id] = {}
        self.message_history[message.guild.id][message.id] = message_data

    async def log_message(self, message: discord.Message):
        """メッセージを記録"""
        if not message.guild or 'message_create' not in self.enabled_events:
            return
            
        try:
            # メッセージをキャッシュ
            await self.add_to_cache(message)
                
            # ログチャンネル取得
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
                        'value': f"{message.author} ({message.author.id})" if self.log_user_ids else str(message.author),
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{message.channel.mention} ({message.channel.id})",
                        'inline': True
                    },
                    {
                        'name': "メッセージID",
                        'value': f"{message.id}",
                        'inline': True
                    }
                ],
                footer=f"メッセージ記録 • ID: {message.id}",
                thumbnail=message.author.display_avatar.url
            )
            
            if attachments:
                embed.add_field(
                    name="添付ファイル",
                    value="\n".join(attachments),
                    inline=False
                )
                
            if self.rich_embed_logs:
                await log_channel.send(embed=embed)
                
            # ファイルにも保存
            await self.save_to_log_file(message.guild.id, 'message_create', {
                'message_id': message.id,
                'author_id': message.author.id,
                'author_name': str(message.author),
                'channel_id': message.channel.id,
                'channel_name': message.channel.name,
                'content': message.content,
                'attachments': [{'url': a.url, 'filename': a.filename} for a in message.attachments],
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error logging message: {e}")

    async def log_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集を記録"""
        if not after.guild or 'message_edit' not in self.enabled_events:
            return
            
        try:
            # メッセージをキャッシュ更新
            await self.add_to_cache(after)
                
            # ログチャンネル取得
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return
                
            # 内容が変更されていない場合は無視
            if before.content == after.content:
                return
                
            # Embedを作成
            embed = self.create_embed(
                title="メッセージ編集",
                description=f"[メッセージに移動]({after.jump_url})",
                color=discord.Color.blue(),
                fields=[
                    {
                        'name': "送信者",
                        'value': f"{after.author} ({after.author.id})" if self.log_user_ids else str(after.author),
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{after.channel.mention} ({after.channel.id})",
                        'inline': True
                    },
                    {
                        'name': "メッセージID",
                        'value': f"{after.id}",
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
                ],
                footer=f"メッセージ編集 • ID: {after.id}",
                thumbnail=after.author.display_avatar.url
            )
            
            if self.rich_embed_logs:
                await log_channel.send(embed=embed)
                
            # ファイルにも保存
            await self.save_to_log_file(after.guild.id, 'message_edit', {
                'message_id': after.id,
                'author_id': after.author.id,
                'author_name': str(after.author),
                'channel_id': after.channel.id,
                'channel_name': after.channel.name,
                'before_content': before.content,
                'after_content': after.content,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error logging message edit: {e}")

    async def log_message_delete(self, message: discord.Message):
        """メッセージ削除を記録"""
        if not message.guild or 'message_delete' not in self.enabled_events:
            return
            
        try:
            # ログチャンネル取得
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
                        'value': f"{message.author} ({message.author.id})" if self.log_user_ids else str(message.author),
                        'inline': True
                    },
                    {
                        'name': "チャンネル",
                        'value': f"{message.channel.mention} ({message.channel.id})",
                        'inline': True
                    },
                    {
                        'name': "メッセージID",
                        'value': f"{message.id}",
                        'inline': True
                    }
                ],
                footer=f"メッセージ削除 • ID: {message.id}",
                thumbnail=message.author.display_avatar.url
            )
            
            if attachments:
                embed.add_field(
                    name="添付ファイル",
                    value="\n".join(attachments),
                    inline=False
                )
                
            if self.rich_embed_logs:
                await log_channel.send(embed=embed)
                
            # キャッシュからメッセージを削除
            if message.guild.id in self.message_cache:
                self.message_cache[message.guild.id] = [m for m in self.message_cache[message.guild.id] if m['id'] != message.id]
                
            # 履歴からも削除（削除フラグを立てる）
            if message.guild.id in self.message_history and message.id in self.message_history[message.guild.id]:
                self.message_history[message.guild.id][message.id]['deleted'] = True
                self.message_history[message.guild.id][message.id]['deleted_at'] = datetime.utcnow().isoformat()
                
            # ファイルにも保存
            await self.save_to_log_file(message.guild.id, 'message_delete', {
                'message_id': message.id,
                'author_id': message.author.id,
                'author_name': str(message.author),
                'channel_id': message.channel.id,
                'channel_name': message.channel.name,
                'content': message.content,
                'attachments': [{'url': a.url, 'filename': a.filename} for a in message.attachments],
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error logging message delete: {e}")

    async def save_to_log_file(self, guild_id: int, event_type: str, data: Dict[str, Any]) -> None:
        """ログをファイルに保存"""
        try:
            log_file_path = await self.get_log_file_path(guild_id, event_type)
            
            # 既存のログを読み込み
            logs = []
            if os.path.exists(log_file_path):
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
                    
            # 新しいログを追加
            logs.append({
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            })
            
            # ログを保存
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving log to file: {e}")
            
    async def load_message_history(self) -> None:
        """メッセージ履歴を読み込む"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    self.message_history = json.load(f)
        except Exception as e:
            logger.error(f"Error loading message history: {e}")
            self.message_history = {}
            
    async def save_message_history(self) -> None:
        """メッセージ履歴を保存"""
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.message_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving message history: {e}")
            
    async def periodic_cleanup(self) -> None:
        """定期的なクリーンアップ処理"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # 古いログを削除
                await self.cleanup_old_logs()
                
                # メッセージ履歴を保存
                await self.save_message_history()
                
                # 24時間待機
                await asyncio.sleep(86400)
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(3600)  # エラー時は1時間後に再試行
                
    async def cleanup_old_logs(self) -> None:
        """古いログを削除"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.log_retention_days)
            
            # メッセージ履歴のクリーンアップ
            for guild_id in list(self.message_history.keys()):
                for message_id in list(self.message_history[guild_id].keys()):
                    try:
                        message_data = self.message_history[guild_id][message_id]
                        created_at = datetime.fromisoformat(message_data['created_at'])
                        
                        if created_at < cutoff_date:
                            del self.message_history[guild_id][message_id]
                    except:
                        # エラーが発生した場合はそのメッセージをスキップ
                        continue
                        
                # 空のギルドエントリを削除
                if not self.message_history[guild_id]:
                    del self.message_history[guild_id]
                    
            # ログファイルのクリーンアップ
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            for guild_id in os.listdir(logs_dir):
                guild_logs_dir = os.path.join(logs_dir, guild_id)
                if os.path.isdir(guild_logs_dir):
                    for log_file in os.listdir(guild_logs_dir):
                        log_file_path = os.path.join(guild_logs_dir, log_file)
                        if os.path.isfile(log_file_path):
                            # ファイルの最終更新日を確認
                            file_mod_time = datetime.fromtimestamp(os.path.getmtime(log_file_path))
                            if file_mod_time < cutoff_date:
                                os.remove(log_file_path)
                                
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            
    async def find_messages(
        self,
        guild: discord.Guild,
        search_term: str = None,
        author: Union[discord.Member, discord.User] = None,
        channel: discord.TextChannel = None,
        before: datetime = None,
        after: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """メッセージを検索"""
        results = []
        
        try:
            if guild.id not in self.message_history:
                return results
                
            guild_history = self.message_history[guild.id]
            
            # フィルタリング条件を適用
            for message_id, message_data in guild_history.items():
                # 削除されたメッセージはスキップ
                if message_data.get('deleted', False):
                    continue
                    
                # 検索条件に合致するか確認
                matches = True
                
                # 著者でフィルタリング
                if author and message_data['author_id'] != author.id:
                    matches = False
                    
                # チャンネルでフィルタリング
                if channel and message_data['channel_id'] != channel.id:
                    matches = False
                    
                # 日時でフィルタリング
                try:
                    created_at = datetime.fromisoformat(message_data['created_at'])
                    if before and created_at > before:
                        matches = False
                    if after and created_at < after:
                        matches = False
                except:
                    # 日付解析エラーの場合はスキップ
                    matches = False
                    
                # 検索語でフィルタリング
                if search_term and search_term.lower() not in message_data.get('content', '').lower():
                    matches = False
                    
                # 条件に合致する場合は結果に追加
                if matches:
                    results.append(message_data)
                    
                    # 上限に達したら終了
                    if len(results) >= limit:
                        break
                        
            # 結果を日時順にソート
            results.sort(key=lambda m: m['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error finding messages: {e}")
            
        return results
        
    async def generate_message_report(
        self,
        guild: discord.Guild,
        author: Optional[Union[discord.Member, discord.User]] = None,
        channel: Optional[discord.TextChannel] = None,
        days: int = 7,
        include_content: bool = False
    ) -> discord.Embed:
        """メッセージ統計レポートを生成"""
        try:
            after = datetime.utcnow() - timedelta(days=days)
            
            # メッセージを検索
            messages = await self.find_messages(
                guild=guild,
                author=author,
                channel=channel,
                after=after,
                limit=10000  # 十分大きな数字
            )
            
            # 統計データを収集
            total_messages = len(messages)
            authors = {}
            channels = {}
            hourly_activity = [0] * 24
            daily_activity = [0] * 7
            
            for message in messages:
                # 著者の統計
                author_id = message['author_id']
                author_name = message['author_name']
                if author_id not in authors:
                    authors[author_id] = {
                        'name': author_name,
                        'count': 0
                    }
                authors[author_id]['count'] += 1
                
                # チャンネルの統計
                channel_id = message['channel_id']
                channel_name = message['channel_name']
                if channel_id not in channels:
                    channels[channel_id] = {
                        'name': channel_name,
                        'count': 0
                    }
                channels[channel_id]['count'] += 1
                
                # 時間帯別統計
                created_at = datetime.fromisoformat(message['created_at'])
                hourly_activity[created_at.hour] += 1
                daily_activity[created_at.weekday()] += 1
                
            # 上位の著者とチャンネルを取得
            top_authors = sorted(authors.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
            top_channels = sorted(channels.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
            
            # 最も活発な時間帯と曜日
            most_active_hour = hourly_activity.index(max(hourly_activity))
            most_active_day = daily_activity.index(max(daily_activity))
            weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            
            # Embedを作成
            title = "メッセージ統計レポート"
            if author:
                title += f" - {author.display_name}"
            if channel:
                title += f" - #{channel.name}"
                
            embed = discord.Embed(
                title=title,
                description=f"過去{days}日間のメッセージ統計",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # 基本統計
            embed.add_field(
                name="総メッセージ数",
                value=f"{total_messages}",
                inline=True
            )
            embed.add_field(
                name="ユニーク投稿者数",
                value=f"{len(authors)}",
                inline=True
            )
            embed.add_field(
                name="投稿チャンネル数",
                value=f"{len(channels)}",
                inline=True
            )
            
            # 活動パターン
            embed.add_field(
                name="最も活発な時間帯",
                value=f"{most_active_hour}時台",
                inline=True
            )
            embed.add_field(
                name="最も活発な曜日",
                value=f"{weekdays[most_active_day]}",
                inline=True
            )
            
            # 上位投稿者
            if top_authors:
                authors_text = "\n".join([f"{idx+1}. {data['name']}: {data['count']}件" for idx, (_, data) in enumerate(top_authors)])
                embed.add_field(
                    name="最もアクティブなユーザー",
                    value=authors_text,
                    inline=False
                )
                
            # 上位チャンネル
            if top_channels:
                channels_text = "\n".join([f"{idx+1}. #{data['name']}: {data['count']}件" for idx, (_, data) in enumerate(top_channels)])
                embed.add_field(
                    name="最もアクティブなチャンネル",
                    value=channels_text,
                    inline=False
                )
                
            # サンプルコンテンツ
            if include_content and messages:
                sample_messages = random.sample(messages, min(3, len(messages)))
                samples_text = "\n\n".join([
                    f"**{msg['author_name']} in #{msg['channel_name']}**\n{msg.get('content', '(内容なし)')[:100]}..."
                    for msg in sample_messages
                ])
                embed.add_field(
                    name="サンプルメッセージ",
                    value=samples_text,
                    inline=False
                )
                
            return embed
            
        except Exception as e:
            logger.error(f"Error generating message report: {e}")
            return discord.Embed(
                title="エラー",
                description=f"レポート生成中にエラーが発生しました: {e}",
                color=discord.Color.red()
            ) 