from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import logging
from modules.utility.server_service import ServerService

logger = logging.getLogger('utility.server')

class Server(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_service = ServerService(bot)

    @app_commands.command(name="serverinfo", description="サーバーの情報を表示します")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        """サーバーの情報を表示します"""
        try:
            info = await self.server_service.get_server_info(interaction.guild)

            embed = discord.Embed(
                title=f"{info['name']}の情報",
                color=discord.Color.blue()
            )

            if info['icon_url']:
                embed.set_thumbnail(url=info['icon_url'])
            if info['banner_url']:
                embed.set_image(url=info['banner_url'])

            # 基本情報
            embed.add_field(
                name="基本情報",
                value=f"ID: {info['id']}\n"
                      f"オーナー: {info['owner'].mention}\n"
                      f"作成日時: {info['created_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                      f"メンバー数: {info['member_count']}\n"
                      f"チャンネル数: {info['channel_count']}\n"
                      f"ロール数: {info['role_count']}\n"
                      f"絵文字数: {info['emoji_count']}",
                inline=False
            )

            # ブースト情報
            embed.add_field(
                name="ブースト情報",
                value=f"レベル: {info['boost_level']}\n"
                      f"ブースト数: {info['boost_count']}",
                inline=True
            )

            # サーバー設定
            embed.add_field(
                name="サーバー設定",
                value=f"認証レベル: {info['verification_level']}\n"
                      f"コンテンツフィルター: {info['explicit_content_filter']}\n"
                      f"通知設定: {info['default_notifications']}",
                inline=True
            )

            # チャンネル設定
            channels = []
            if info['afk_channel']:
                channels.append(f"AFK: {info['afk_channel']} ({info['afk_timeout']}秒)")
            if info['system_channel']:
                channels.append(f"システム: {info['system_channel']}")
            if info['rules_channel']:
                channels.append(f"ルール: {info['rules_channel']}")
            if info['public_updates_channel']:
                channels.append(f"アップデート: {info['public_updates_channel']}")

            if channels:
                embed.add_field(
                    name="チャンネル設定",
                    value="\n".join(channels),
                    inline=False
                )

            # BOT設定
            bot_settings = []
            if info.get('prefix'):
                bot_settings.append(f"プレフィックス: {info['prefix']}")
            if info.get('language'):
                bot_settings.append(f"言語: {info['language']}")
            if info.get('mod_role'):
                bot_settings.append(f"モデレーターロール: {info['mod_role']}")
            if info.get('admin_role'):
                bot_settings.append(f"管理者ロール: {info['admin_role']}")
            if info.get('log_channel'):
                bot_settings.append(f"ログチャンネル: {info['log_channel']}")
            if info.get('welcome_channel'):
                bot_settings.append(f"ウェルカムチャンネル: {info['welcome_channel']}")

            if bot_settings:
                embed.add_field(
                    name="BOT設定",
                    value="\n".join(bot_settings),
                    inline=False
                )

            # 保護機能
            protection = []
            if info.get('spam_protection'):
                protection.append("スパム対策: 有効")
            if info.get('raid_protection'):
                protection.append("レイド対策: 有効")

            if protection:
                embed.add_field(
                    name="保護機能",
                    value="\n".join(protection),
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "サーバー情報の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get server info: {e}")

    @app_commands.command(name="settings", description="サーバーの設定を変更します")
    @app_commands.describe(
        setting="変更する設定",
        value="新しい値",
        reason="変更理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(
        self,
        interaction: discord.Interaction,
        setting: Literal[
            "名前", "説明", "AFKチャンネル", "AFKタイムアウト",
            "認証レベル", "通知設定", "コンテンツフィルター",
            "システムチャンネル", "プレフィックス", "言語",
            "モデレーターロール", "管理者ロール", "ログチャンネル",
            "ウェルカムチャンネル", "ウェルカムメッセージ",
            "退出メッセージ", "スパム対策", "レイド対策"
        ],
        value: str,
        reason: Optional[str] = None
    ):
        """サーバーの設定を変更します"""
        try:
            settings = {}

            # 設定値を解析
            if setting == "名前":
                settings['name'] = value
            elif setting == "説明":
                settings['description'] = value
            elif setting == "AFKチャンネル":
                channel = await commands.TextChannelConverter().convert(interaction, value)
                settings['afk_channel'] = channel
            elif setting == "AFKタイムアウト":
                timeout = int(value)
                if timeout not in [60, 300, 900, 1800, 3600]:
                    raise ValueError("タイムアウトは60, 300, 900, 1800, 3600秒のいずれかである必要があります。")
                settings['afk_timeout'] = timeout
            elif setting == "認証レベル":
                settings['verification_level'] = discord.VerificationLevel[value.upper()]
            elif setting == "通知設定":
                settings['default_notifications'] = discord.NotificationLevel[value.upper()]
            elif setting == "コンテンツフィルター":
                settings['explicit_content_filter'] = discord.ContentFilter[value.upper()]
            elif setting == "システムチャンネル":
                channel = await commands.TextChannelConverter().convert(interaction, value)
                settings['system_channel'] = channel
            elif setting == "プレフィックス":
                settings['prefix'] = value
            elif setting == "言語":
                if value not in ['ja', 'en']:
                    raise ValueError("言語はjaまたはenである必要があります。")
                settings['language'] = value
            elif setting == "モデレーターロール":
                role = await commands.RoleConverter().convert(interaction, value)
                settings['mod_role_id'] = role.id
            elif setting == "管理者ロール":
                role = await commands.RoleConverter().convert(interaction, value)
                settings['admin_role_id'] = role.id
            elif setting == "ログチャンネル":
                channel = await commands.TextChannelConverter().convert(interaction, value)
                settings['log_channel_id'] = channel.id
            elif setting == "ウェルカムチャンネル":
                channel = await commands.TextChannelConverter().convert(interaction, value)
                settings['welcome_channel_id'] = channel.id
            elif setting == "ウェルカムメッセージ":
                settings['welcome_message'] = value
            elif setting == "退出メッセージ":
                settings['leave_message'] = value
            elif setting == "スパム対策":
                settings['spam_protection'] = value.lower() == "true"
            elif setting == "レイド対策":
                settings['raid_protection'] = value.lower() == "true"

            # 設定を更新
            result = await self.server_service.update_server_settings(
                interaction.guild,
                settings,
                reason
            )

            await interaction.response.send_message(result)

        except ValueError as e:
            await interaction.response.send_message(
                f"無効な値です: {str(e)}",
                ephemeral=True
            )
        except commands.BadArgument:
            await interaction.response.send_message(
                "指定された値が見つかりません。",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "設定の更新中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to update settings: {e}")

    @app_commands.command(name="createinvite", description="招待リンクを作成します")
    @app_commands.describe(
        channel="招待リンクを作成するチャンネル",
        max_age="リンクの有効期限（秒、0で無期限）",
        max_uses="使用可能回数（0で無制限）",
        temporary="一時的なメンバーシップを付与するかどうか",
        unique="一意の招待リンクを作成するかどうか",
        reason="作成理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(create_instant_invite=True)
    async def createinvite(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        max_age: Optional[int] = 0,
        max_uses: Optional[int] = 0,
        temporary: Optional[bool] = False,
        unique: Optional[bool] = True,
        reason: Optional[str] = None
    ):
        """招待リンクを作成します"""
        try:
            channel = channel or interaction.channel
            invite, message = await self.server_service.create_invite(
                channel,
                max_age,
                max_uses,
                temporary,
                unique,
                reason
            )

            if invite:
                embed = discord.Embed(
                    title="招待リンクを作成しました",
                    color=discord.Color.green()
                )
                embed.add_field(name="リンク", value=f"discord.gg/{invite.code}", inline=False)
                embed.add_field(name="チャンネル", value=channel.mention, inline=True)
                if max_age > 0:
                    embed.add_field(name="有効期限", value=f"{max_age}秒", inline=True)
                if max_uses > 0:
                    embed.add_field(name="使用可能回数", value=str(max_uses), inline=True)
                if temporary:
                    embed.add_field(name="一時的メンバーシップ", value="有効", inline=True)
                if reason:
                    embed.add_field(name="理由", value=reason, inline=False)

                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "招待リンクの作成中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to create invite: {e}")

    @app_commands.command(name="invites", description="サーバーの招待リンク一覧を表示します")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def invites(self, interaction: discord.Interaction):
        """サーバーの招待リンク一覧を表示します"""
        try:
            invites = await self.server_service.get_invites(interaction.guild)

            if not invites:
                await interaction.response.send_message(
                    "招待リンクが見つかりません。",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="招待リンク一覧",
                color=discord.Color.blue()
            )

            for invite in invites:
                value = f"作成者: {invite.inviter.mention if invite.inviter else '不明'}\n"
                value += f"チャンネル: {invite.channel.mention}\n"
                value += f"使用回数: {invite.uses}\n"
                if invite.max_uses:
                    value += f"使用可能回数: {invite.max_uses}\n"
                if invite.max_age:
                    value += f"有効期限: {invite.max_age}秒\n"
                if invite.temporary:
                    value += "一時的メンバーシップ: 有効\n"
                value += f"作成日時: {invite.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"

                embed.add_field(
                    name=f"discord.gg/{invite.code}",
                    value=value,
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "招待リンクの取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get invites: {e}")

    @app_commands.command(name="deleteinvite", description="招待リンクを削除します")
    @app_commands.describe(
        code="削除する招待リンクのコード",
        reason="削除理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def deleteinvite(
        self,
        interaction: discord.Interaction,
        code: str,
        reason: Optional[str] = None
    ):
        """招待リンクを削除します"""
        try:
            invites = await self.server_service.get_invites(interaction.guild)
            invite = discord.utils.get(invites, code=code)

            if not invite:
                await interaction.response.send_message(
                    "指定された招待リンクが見つかりません。",
                    ephemeral=True
                )
                return

            result = await self.server_service.delete_invite(invite, reason)
            await interaction.response.send_message(result)

        except Exception as e:
            await interaction.response.send_message(
                "招待リンクの削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to delete invite: {e}")

    @app_commands.command(name="auditlog", description="監査ログを表示します")
    @app_commands.describe(
        action_type="表示するアクションの種類",
        user="特定のユーザーのログのみを表示",
        limit="表示する最大件数"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(view_audit_log=True)
    async def auditlog(
        self,
        interaction: discord.Interaction,
        action_type: Optional[str] = None,
        user: Optional[discord.Member] = None,
        limit: Optional[int] = 10
    ):
        """監査ログを表示します"""
        try:
            logs = await self.server_service.get_audit_logs(
                interaction.guild,
                limit,
                action_type,
                user
            )

            if not logs:
                await interaction.response.send_message(
                    "監査ログが見つかりません。",
                    ephemeral=True
                )
                return

            embeds = []
            current_embed = discord.Embed(
                title="監査ログ",
                color=discord.Color.blue()
            )
            field_count = 0

            for log in logs:
                value = f"実行者: {log['actor']}\n"
                if log['target']:
                    value += f"対象: {log['target']}\n"
                value += f"理由: {log['reason']}\n"
                if log['details']:
                    value += f"詳細: {log['details']}\n"
                value += f"日時: {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} UTC"

                # 25フィールドごとに新しいEmbedを作成
                if field_count >= 25:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(
                        title="監査ログ（続き）",
                        color=discord.Color.blue()
                    )
                    field_count = 0

                current_embed.add_field(
                    name=f"#{log['id']} - {log['action_type']}",
                    value=value,
                    inline=False
                )
                field_count += 1

            embeds.append(current_embed)

            # 最初のEmbedを送信
            await interaction.response.send_message(embed=embeds[0])

            # 残りのEmbedを送信
            for embed in embeds[1:]:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "監査ログの取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get audit logs: {e}")

    @settings.error
    @createinvite.error
    @invites.error
    @deleteinvite.error
    @auditlog.error
    async def server_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """サーバー管理コマンドのエラーハンドリング"""
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
            logger.error(f"Error in server command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Server(bot)) 