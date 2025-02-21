from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, Literal
import logging
from ...modules.utility.channel_service import ChannelService

logger = logging.getLogger('utility.channel')

class Channel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_service = ChannelService(bot)

    @app_commands.command(name="createchannel", description="新しいチャンネルを作成します")
    @app_commands.describe(
        name="チャンネル名",
        type="チャンネルの種類",
        category="所属するカテゴリ",
        topic="チャンネルのトピック",
        nsfw="NSFWチャンネルかどうか",
        reason="作成理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def createchannel(
        self,
        interaction: discord.Interaction,
        name: str,
        type: Literal["テキスト", "ボイス"],
        category: Optional[discord.CategoryChannel] = None,
        topic: Optional[str] = None,
        nsfw: Optional[bool] = False,
        reason: Optional[str] = None
    ):
        """
        新しいチャンネルを作成します。
        
        Parameters
        ----------
        name : str
            チャンネル名
        type : Literal["テキスト", "ボイス"]
            チャンネルの種類
        category : discord.CategoryChannel, optional
            所属するカテゴリ
        topic : str, optional
            チャンネルのトピック
        nsfw : bool, optional
            NSFWチャンネルかどうか
        reason : str, optional
            作成理由
        """
        try:
            # チャンネルの種類を変換
            channel_type = discord.ChannelType.text if type == "テキスト" else discord.ChannelType.voice

            # チャンネルを作成
            channel, message = await self.channel_service.create_channel(
                guild=interaction.guild,
                name=name,
                channel_type=channel_type,
                category=category,
                topic=topic,
                nsfw=nsfw,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="チャンネルを作成しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="チャンネル", value=channel.mention, inline=False)
            embed.add_field(name="種類", value=type, inline=True)
            if category:
                embed.add_field(name="カテゴリ", value=category.name, inline=True)
            if topic:
                embed.add_field(name="トピック", value=topic, inline=True)
            if nsfw:
                embed.add_field(name="NSFW", value="有効", inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "チャンネルの作成中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to create channel: {e}")

    @app_commands.command(name="deletechannel", description="チャンネルを削除します")
    @app_commands.describe(
        channel="削除するチャンネル",
        reason="削除理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def deletechannel(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        reason: Optional[str] = None
    ):
        """
        チャンネルを削除します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            削除するチャンネル
        reason : str, optional
            削除理由
        """
        try:
            # チャンネルを削除
            message = await self.channel_service.delete_channel(
                channel=channel,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="チャンネルを削除しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="チャンネル名", value=channel.name, inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "チャンネルの削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to delete channel: {e}")

    @app_commands.command(name="modifychannel", description="チャンネルの設定を変更します")
    @app_commands.describe(
        channel="変更するチャンネル",
        name="新しいチャンネル名",
        topic="新しいトピック",
        nsfw="NSFWチャンネルかどうか",
        category="新しいカテゴリ",
        sync_permissions="カテゴリの権限と同期するかどうか",
        reason="変更理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def modifychannel(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        name: Optional[str] = None,
        topic: Optional[str] = None,
        nsfw: Optional[bool] = None,
        category: Optional[discord.CategoryChannel] = None,
        sync_permissions: Optional[bool] = False,
        reason: Optional[str] = None
    ):
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
        category : discord.CategoryChannel, optional
            新しいカテゴリ
        sync_permissions : bool, optional
            カテゴリの権限と同期するかどうか
        reason : str, optional
            変更理由
        """
        try:
            # チャンネルを更新
            message = await self.channel_service.modify_channel(
                channel=channel,
                name=name,
                topic=topic,
                nsfw=nsfw,
                category=category,
                sync_permissions=sync_permissions,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="チャンネルを更新しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="チャンネル", value=channel.mention, inline=False)
            if name:
                embed.add_field(name="新しい名前", value=name, inline=True)
            if topic:
                embed.add_field(name="新しいトピック", value=topic, inline=True)
            if nsfw is not None:
                embed.add_field(name="NSFW", value="有効" if nsfw else "無効", inline=True)
            if category:
                embed.add_field(name="新しいカテゴリ", value=category.name, inline=True)
            if sync_permissions:
                embed.add_field(name="権限同期", value="有効", inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "チャンネルの更新中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to modify channel: {e}")

    @app_commands.command(name="channels", description="サーバーのチャンネル一覧を表示します")
    @app_commands.describe(
        type="表示するチャンネルの種類"
    )
    @app_commands.guild_only()
    async def channels(
        self,
        interaction: discord.Interaction,
        type: Optional[Literal["テキスト", "ボイス"]] = None
    ):
        """
        サーバーのチャンネル一覧を表示します。
        
        Parameters
        ----------
        type : Literal["テキスト", "ボイス"], optional
            表示するチャンネルの種類
        """
        try:
            # チャンネルの種類を変換
            channel_type = None
            if type:
                channel_type = discord.ChannelType.text if type == "テキスト" else discord.ChannelType.voice

            # チャンネル一覧を取得
            channels = await self.channel_service.list_channels(
                guild=interaction.guild,
                channel_type=channel_type
            )

            # チャンネルをカテゴリごとに分類
            categories = {}
            no_category = []
            for channel in channels:
                if channel.category:
                    if channel.category.name not in categories:
                        categories[channel.category.name] = []
                    categories[channel.category.name].append(channel)
                else:
                    no_category.append(channel)

            # 結果を表示
            embed = discord.Embed(
                title=f"{interaction.guild.name} のチャンネル一覧",
                color=discord.Color.blue()
            )

            # カテゴリなしのチャンネルを表示
            if no_category:
                value = "\n".join([
                    f"{channel.mention} ({str(channel.type).split('.')[-1]})"
                    for channel in no_category
                ])
                embed.add_field(
                    name="カテゴリなし",
                    value=value,
                    inline=False
                )

            # カテゴリごとにチャンネルを表示
            for category, channels in categories.items():
                value = "\n".join([
                    f"{channel.mention} ({str(channel.type).split('.')[-1]})"
                    for channel in channels
                ])
                embed.add_field(
                    name=category,
                    value=value,
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "チャンネル一覧の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to list channels: {e}")

    @app_commands.command(name="channelinfo", description="チャンネルの詳細情報を表示します")
    @app_commands.describe(
        channel="情報を表示するチャンネル"
    )
    @app_commands.guild_only()
    async def channelinfo(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.TextChannel, discord.VoiceChannel]
    ):
        """
        チャンネルの詳細情報を表示します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            情報を表示するチャンネル
        """
        try:
            # チャンネル情報を取得
            info = await self.channel_service.get_channel_info(channel)

            # 情報を表示
            embed = discord.Embed(
                title=f"チャンネル情報: {info['name']}",
                color=discord.Color.blue()
            )
            embed.add_field(name="ID", value=info['id'], inline=True)
            embed.add_field(name="種類", value=info['type'], inline=True)
            embed.add_field(name="位置", value=info['position'], inline=True)
            if info['category']:
                embed.add_field(name="カテゴリ", value=info['category'], inline=True)
            if 'topic' in info:
                embed.add_field(name="トピック", value=info['topic'] or "なし", inline=True)
            if 'nsfw' in info:
                embed.add_field(name="NSFW", value="有効" if info['nsfw'] else "無効", inline=True)
            if 'slowmode_delay' in info:
                embed.add_field(name="低速モード", value=f"{info['slowmode_delay']}秒", inline=True)
            embed.add_field(name="作成日時", value=info['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)

            # 権限情報を表示
            if info['permissions']:
                permissions = []
                for target, perms in info['permissions'].items():
                    type_str = "ロール" if perms['type'] == 'role' else "メンバー"
                    permissions.append(f"{target} ({type_str})")
                embed.add_field(
                    name="権限設定",
                    value="\n".join(permissions),
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "チャンネル情報の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get channel info: {e}")

    @app_commands.command(name="setpermissions", description="チャンネルの権限を設定します")
    @app_commands.describe(
        channel="設定するチャンネル",
        target="対象のロールまたはメンバー",
        allow="許可する権限（カンマ区切り）",
        deny="拒否する権限（カンマ区切り）",
        reason="変更理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setpermissions(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        target: Union[discord.Role, discord.Member],
        allow: Optional[str] = None,
        deny: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """
        チャンネルの権限を設定します。
        
        Parameters
        ----------
        channel : Union[discord.TextChannel, discord.VoiceChannel]
            設定するチャンネル
        target : Union[discord.Role, discord.Member]
            対象のロールまたはメンバー
        allow : str, optional
            許可する権限（カンマ区切り）
        deny : str, optional
            拒否する権限（カンマ区切り）
        reason : str, optional
            変更理由
        """
        try:
            # 権限を設定
            overwrite = discord.PermissionOverwrite()

            # 許可する権限を設定
            if allow:
                for perm in allow.split(','):
                    perm = perm.strip().lower()
                    if hasattr(discord.Permissions, perm):
                        setattr(overwrite, perm, True)

            # 拒否する権限を設定
            if deny:
                for perm in deny.split(','):
                    perm = perm.strip().lower()
                    if hasattr(discord.Permissions, perm):
                        setattr(overwrite, perm, False)

            # 権限を更新
            message = await self.channel_service.set_permissions(
                channel=channel,
                target=target,
                overwrite=overwrite if allow or deny else None,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="チャンネルの権限を設定しました",
                color=discord.Color.blue()
            )
            embed.add_field(name="チャンネル", value=channel.mention, inline=False)
            embed.add_field(
                name="対象",
                value=f"{target.mention} ({'ロール' if isinstance(target, discord.Role) else 'メンバー'})",
                inline=False
            )
            if allow:
                embed.add_field(name="許可した権限", value=allow, inline=True)
            if deny:
                embed.add_field(name="拒否した権限", value=deny, inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "権限の設定中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to set permissions: {e}")

    @createchannel.error
    @deletechannel.error
    @modifychannel.error
    @setpermissions.error
    async def channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """チャンネルコマンドのエラーハンドリング"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "このコマンドを実行する権限がありません。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "コマンドの実行中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Error in channel command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Channel(bot)) 