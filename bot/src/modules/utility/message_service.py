import discord
from discord.ext import commands
from typing import List, Optional, Dict, Union, Tuple
import logging
from datetime import datetime, timedelta
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.message')

class MessageService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def bulk_delete(
        self,
        channel: discord.TextChannel,
        limit: int,
        user: Optional[discord.Member] = None,
        contains: Optional[str] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        メッセージを一括削除します。

        Parameters
        ----------
        channel : discord.TextChannel
            対象チャンネル
        limit : int
            削除する最大メッセージ数
        user : discord.Member, optional
            特定のユーザーのメッセージのみを削除
        contains : str, optional
            特定の文字列を含むメッセージのみを削除
        before : datetime, optional
            この日時より前のメッセージを削除
        after : datetime, optional
            この日時より後のメッセージを削除
        reason : str, optional
            削除理由

        Returns
        -------
        Tuple[int, str]
            削除したメッセージ数と結果メッセージ
        """
        try:
            def check_message(message: discord.Message) -> bool:
                if user and message.author != user:
                    return False
                if contains and contains not in message.content:
                    return False
                if before and message.created_at >= before:
                    return False
                if after and message.created_at <= after:
                    return False
                return True

            messages = []
            async for message in channel.history(limit=limit):
                if check_message(message):
                    messages.append(message)

            if not messages:
                return 0, "条件に一致するメッセージが見つかりませんでした。"

            # 2週間以上前のメッセージは一括削除できない
            now = datetime.utcnow()
            old_messages = [m for m in messages if (now - m.created_at).days >= 14]
            recent_messages = [m for m in messages if (now - m.created_at).days < 14]

            deleted_count = 0

            # 最近のメッセージを一括削除
            if recent_messages:
                await channel.delete_messages(recent_messages)
                deleted_count += len(recent_messages)

            # 古いメッセージを個別に削除
            for message in old_messages:
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.NotFound:
                    continue

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="bulk_delete",
                    user_id=self.bot.user.id,
                    target_id=channel.id,
                    reason=reason or "一括削除",
                    details={
                        'deleted_count': deleted_count,
                        'channel_name': channel.name,
                        'user_filter': str(user) if user else None,
                        'content_filter': contains
                    }
                )

            return deleted_count, f"{deleted_count}件のメッセージを削除しました。"

        except discord.Forbidden:
            return 0, "メッセージの削除権限がありません。"
        except discord.HTTPException as e:
            logger.error(f"Failed to bulk delete messages: {e}")
            return 0, "メッセージの削除中にエラーが発生しました。"

    async def pin_message(
        self,
        message: discord.Message,
        reason: Optional[str] = None
    ) -> str:
        """
        メッセージをピン留めします。

        Parameters
        ----------
        message : discord.Message
            ピン留めするメッセージ
        reason : str, optional
            ピン留めの理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            await message.pin(reason=reason)
            
            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=message.guild.id,
                    action_type="pin_message",
                    user_id=self.bot.user.id,
                    target_id=message.id,
                    reason=reason or "メッセージをピン留め",
                    details={
                        'channel_name': message.channel.name,
                        'message_content': message.content[:100]
                    }
                )

            return "メッセージをピン留めしました。"

        except discord.Forbidden:
            return "メッセージのピン留め権限がありません。"
        except discord.HTTPException as e:
            logger.error(f"Failed to pin message: {e}")
            return "メッセージのピン留め中にエラーが発生しました。"

    async def unpin_message(
        self,
        message: discord.Message,
        reason: Optional[str] = None
    ) -> str:
        """
        メッセージのピン留めを解除します。

        Parameters
        ----------
        message : discord.Message
            ピン留めを解除するメッセージ
        reason : str, optional
            解除の理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            await message.unpin(reason=reason)
            
            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=message.guild.id,
                    action_type="unpin_message",
                    user_id=self.bot.user.id,
                    target_id=message.id,
                    reason=reason or "ピン留めを解除",
                    details={
                        'channel_name': message.channel.name,
                        'message_content': message.content[:100]
                    }
                )

            return "メッセージのピン留めを解除しました。"

        except discord.Forbidden:
            return "メッセージのピン留め解除権限がありません。"
        except discord.HTTPException as e:
            logger.error(f"Failed to unpin message: {e}")
            return "メッセージのピン留め解除中にエラーが発生しました。"

    async def move_message(
        self,
        message: discord.Message,
        destination: discord.TextChannel,
        reason: Optional[str] = None
    ) -> str:
        """
        メッセージを別のチャンネルに移動（コピー）します。

        Parameters
        ----------
        message : discord.Message
            移動するメッセージ
        destination : discord.TextChannel
            移動先のチャンネル
        reason : str, optional
            移動の理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # 新しいメッセージを作成
            embed = discord.Embed(
                description=message.content,
                timestamp=message.created_at,
                color=discord.Color.blue()
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            embed.add_field(
                name="元のチャンネル",
                value=message.channel.mention,
                inline=False
            )

            # 添付ファイルがある場合は追加
            if message.attachments:
                attachment_links = []
                for attachment in message.attachments:
                    if attachment.url:
                        attachment_links.append(f"[{attachment.filename}]({attachment.url})")
                if attachment_links:
                    embed.add_field(
                        name="添付ファイル",
                        value="\n".join(attachment_links),
                        inline=False
                    )

            # 移動先にメッセージを送信
            await destination.send(embed=embed)

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=message.guild.id,
                    action_type="move_message",
                    user_id=self.bot.user.id,
                    target_id=message.id,
                    reason=reason or "メッセージを移動",
                    details={
                        'source_channel': message.channel.name,
                        'destination_channel': destination.name,
                        'message_content': message.content[:100]
                    }
                )

            return f"メッセージを {destination.mention} に移動しました。"

        except discord.Forbidden:
            return "メッセージの移動権限がありません。"
        except discord.HTTPException as e:
            logger.error(f"Failed to move message: {e}")
            return "メッセージの移動中にエラーが発生しました。"

    async def search_messages(
        self,
        channel: discord.TextChannel,
        query: str,
        user: Optional[discord.Member] = None,
        limit: int = 100
    ) -> List[discord.Message]:
        """
        メッセージを検索します。

        Parameters
        ----------
        channel : discord.TextChannel
            検索対象のチャンネル
        query : str
            検索クエリ
        user : discord.Member, optional
            特定のユーザーのメッセージのみを検索
        limit : int, optional
            検索する最大メッセージ数

        Returns
        -------
        List[discord.Message]
            検索結果のメッセージリスト
        """
        try:
            results = []
            async for message in channel.history(limit=limit):
                if query.lower() in message.content.lower():
                    if user is None or message.author == user:
                        results.append(message)

            return results

        except discord.Forbidden:
            logger.error("Missing permissions to search messages")
            return []
        except discord.HTTPException as e:
            logger.error(f"Failed to search messages: {e}")
            return []

    async def get_message_history(
        self,
        message: discord.Message
    ) -> List[Dict]:
        """
        メッセージの編集履歴を取得します。

        Parameters
        ----------
        message : discord.Message
            対象のメッセージ

        Returns
        -------
        List[Dict]
            編集履歴のリスト
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                # 監査ログから編集履歴を取得
                audit_logs = await db.get_audit_logs(message.guild.id)
                
                history = []
                for log in audit_logs:
                    if (log.action_type == "message_edit" and 
                        log.target_id == message.id):
                        history.append({
                            'content': log.details.get('content', '不明'),
                            'editor': log.user_id,
                            'timestamp': log.created_at
                        })

                return history

        except Exception as e:
            logger.error(f"Failed to get message history: {e}")
            return [] 