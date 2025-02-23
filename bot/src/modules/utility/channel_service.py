from typing import Dict, List, Optional, Union, Tuple
import discord
from discord.ext import commands
import logging
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.channel')

class ChannelService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_channel(
        self,
        guild: discord.Guild,
        name: str,
        channel_type: discord.ChannelType,
        category: Optional[discord.CategoryChannel] = None,
        topic: Optional[str] = None,
        nsfw: bool = False,
        position: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Tuple[Union[discord.TextChannel, discord.VoiceChannel], str]:
        """
        新しいチャンネルを作成します。
        
        Parameters
        ----------
        guild : discord.Guild
            サーバー
        name : str
            チャンネル名
        channel_type : discord.ChannelType
            チャンネルの種類
        category : discord.CategoryChannel, optional
            所属するカテゴリ
        topic : str, optional
            チャンネルのトピック
        nsfw : bool
            NSFWチャンネルかどうか
        position : int, optional
            チャンネルの位置
        reason : str, optional
            作成理由
            
        Returns
        -------
        Tuple[Union[discord.TextChannel, discord.VoiceChannel], str]
            作成されたチャンネルとメッセージ
        """
        try:
            # チャンネルを作成
            channel = await guild.create_channel(
                name=name,
                type=channel_type,
                category=category,
                topic=topic,
                nsfw=nsfw,
                position=position,
                reason=reason
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=guild.id,
                    action_type="channel_create",
                    user_id=self.bot.user.id,
                    target_id=channel.id,
                    reason=reason,
                    details={
                        'name': name,
                        'type': str(channel_type),
                        'category': category.id if category else None,
                        'topic': topic,
                        'nsfw': nsfw,
                        'position': position
                    }
                )

            return channel, "チャンネルを作成しました。"

        except discord.Forbidden:
            raise ValueError("チャンネルの作成権限がありません。")
        except discord.HTTPException as e:
            logger.error(f"Failed to create channel: {e}")
            raise ValueError("チャンネルの作成中にエラーが発生しました。")

    async def delete_channel(
        self,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        reason: Optional[str] = None
    ) -> str:
        """
        チャンネルを削除します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            削除するチャンネル
        reason : str, optional
            削除理由
            
        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="channel_delete",
                    user_id=self.bot.user.id,
                    target_id=channel.id,
                    reason=reason,
                    details={
                        'name': channel.name,
                        'type': str(channel.type)
                    }
                )

            # チャンネルを削除
            await channel.delete(reason=reason)
            return "チャンネルを削除しました。"

        except discord.Forbidden:
            raise ValueError("チャンネルの削除権限がありません。")
        except discord.HTTPException as e:
            logger.error(f"Failed to delete channel: {e}")
            raise ValueError("チャンネルの削除中にエラーが発生しました。")

    async def modify_channel(
        self,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        name: Optional[str] = None,
        topic: Optional[str] = None,
        nsfw: Optional[bool] = None,
        position: Optional[int] = None,
        category: Optional[discord.CategoryChannel] = None,
        sync_permissions: bool = False,
        reason: Optional[str] = None
    ) -> str:
        """
        チャンネルの設定を変更します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            変更するチャンネル
        name : str, optional
            新しいチャンネル名
        topic : str, optional
            新しいトピック
        nsfw : bool, optional
            NSFWチャンネルかどうか
        position : int, optional
            新しい位置
        category : discord.CategoryChannel, optional
            新しいカテゴリ
        sync_permissions : bool
            カテゴリの権限と同期するかどうか
        reason : str, optional
            変更理由
            
        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # 変更内容を記録
            changes = {}
            if name:
                changes['name'] = name
            if topic is not None and isinstance(channel, discord.TextChannel):
                changes['topic'] = topic
            if nsfw is not None and isinstance(channel, discord.TextChannel):
                changes['nsfw'] = nsfw
            if position is not None:
                changes['position'] = position
            if category:
                changes['category'] = category.id

            # チャンネルを更新
            await channel.edit(
                name=name if name else channel.name,
                topic=topic if topic is not None else channel.topic if isinstance(channel, discord.TextChannel) else None,
                nsfw=nsfw if nsfw is not None else channel.nsfw if isinstance(channel, discord.TextChannel) else False,
                position=position if position is not None else channel.position,
                category=category,
                sync_permissions=sync_permissions,
                reason=reason
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="channel_modify",
                    user_id=self.bot.user.id,
                    target_id=channel.id,
                    reason=reason,
                    details=changes
                )

            return "チャンネルの設定を変更しました。"

        except discord.Forbidden:
            raise ValueError("チャンネルの変更権限がありません。")
        except discord.HTTPException as e:
            logger.error(f"Failed to modify channel: {e}")
            raise ValueError("チャンネルの変更中にエラーが発生しました。")

    async def set_permissions(
        self,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        target: Union[discord.Role, discord.Member],
        overwrite: Optional[discord.PermissionOverwrite] = None,
        reason: Optional[str] = None
    ) -> str:
        """
        チャンネルの権限を設定します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            設定するチャンネル
        target : Union[discord.Role, discord.Member]
            対象のロールまたはメンバー
        overwrite : discord.PermissionOverwrite, optional
            権限設定（Noneの場合は権限を削除）
        reason : str, optional
            変更理由
            
        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # 権限を設定
            await channel.set_permissions(
                target,
                overwrite=overwrite,
                reason=reason
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="channel_permissions",
                    user_id=self.bot.user.id,
                    target_id=target.id,
                    reason=reason,
                    details={
                        'channel_id': channel.id,
                        'channel_name': channel.name,
                        'target_type': 'role' if isinstance(target, discord.Role) else 'member',
                        'target_name': target.name,
                        'permissions': overwrite.pair()[0].value if overwrite else None
                    }
                )

            action = "設定" if overwrite else "削除"
            return f"チャンネルの権限を{action}しました。"

        except discord.Forbidden:
            raise ValueError("権限の変更権限がありません。")
        except discord.HTTPException as e:
            logger.error(f"Failed to set channel permissions: {e}")
            raise ValueError("権限の変更中にエラーが発生しました。")

    async def list_channels(
        self,
        guild: discord.Guild,
        channel_type: Optional[discord.ChannelType] = None
    ) -> List[Union[discord.TextChannel, discord.VoiceChannel]]:
        """
        チャンネル一覧を取得します。
        
        Parameters
        ----------
        guild : discord.Guild
            サーバー
        channel_type : discord.ChannelType, optional
            チャンネルの種類でフィルタ
            
        Returns
        -------
        List[Union[discord.TextChannel, discord.VoiceChannel]]
            チャンネルのリスト
        """
        channels = []
        for channel in guild.channels:
            if channel_type is None or channel.type == channel_type:
                channels.append(channel)
        return sorted(channels, key=lambda c: c.position)

    async def get_channel_info(
        self,
        channel: Union[discord.TextChannel, discord.VoiceChannel]
    ) -> Dict:
        """
        チャンネルの詳細情報を取得します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            情報を取得するチャンネル
            
        Returns
        -------
        Dict
            チャンネル情報の辞書
        """
        info = {
            'id': channel.id,
            'name': channel.name,
            'type': str(channel.type),
            'position': channel.position,
            'created_at': channel.created_at,
            'category': channel.category.name if channel.category else None,
            'permissions': {}
        }

        if isinstance(channel, discord.TextChannel):
            info.update({
                'topic': channel.topic,
                'nsfw': channel.nsfw,
                'slowmode_delay': channel.slowmode_delay
            })

        # 権限情報を追加
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            info['permissions'][target.name] = {
                'type': 'role' if isinstance(target, discord.Role) else 'member',
                'id': target.id,
                'allow': allow.value,
                'deny': deny.value
            }

        return info 