from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, List, Literal
import logging
from ...modules.utility.automod_service import AutoModService

logger = logging.getLogger('utility.automod')

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.automod_service = AutoModService(bot)

    @app_commands.command(name="automod", description="自動モデレーションの設定を表示します")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(self, interaction: discord.Interaction):
        """自動モデレーションの設定を表示します"""
        try:
            settings = await self.automod_service.get_automod_settings(interaction.guild.id)

            embed = discord.Embed(
                title="自動モデレーション設定",
                color=discord.Color.blue()
            )

            # スパム保護
            embed.add_field(
                name="スパム保護",
                value="有効" if settings.get('spam_protection') else "無効",
                inline=True
            )

            # メンション制限
            embed.add_field(
                name="メンション制限",
                value=f"最大 {settings.get('max_mentions', '制限なし')} 個",
                inline=True
            )

            # リンク制限
            embed.add_field(
                name="招待リンク制限",
                value="有効" if settings.get('block_invites') else "無効",
                inline=True
            )
            embed.add_field(
                name="外部リンク制限",
                value="有効" if settings.get('block_links') else "無効",
                inline=True
            )

            # 大文字制限
            embed.add_field(
                name="大文字制限",
                value=f"閾値 {settings.get('caps_threshold', '制限なし')}",
                inline=True
            )

            # 絵文字制限
            embed.add_field(
                name="絵文字制限",
                value=f"最大 {settings.get('max_emojis', '制限なし')} 個",
                inline=True
            )

            # 警告設定
            embed.add_field(
                name="警告設定",
                value=f"最大 {settings.get('max_warnings', 5)} 回\n"
                      f"アクション: {settings.get('action', 'なし')}",
                inline=True
            )

            # タイムアウト設定
            if settings.get('action') == 'timeout':
                embed.add_field(
                    name="タイムアウト期間",
                    value=f"{settings.get('timeout_duration', 3600)}秒",
                    inline=True
                )

            # ログチャンネル
            log_channel = interaction.guild.get_channel(settings.get('log_channel_id'))
            embed.add_field(
                name="ログチャンネル",
                value=log_channel.mention if log_channel else "未設定",
                inline=True
            )

            # 禁止ワード
            if settings.get('banned_words'):
                embed.add_field(
                    name="禁止ワード",
                    value=f"{len(settings['banned_words'])}個設定済み",
                    inline=True
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "設定の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get automod settings: {e}")

    @app_commands.command(name="automod_set", description="自動モデレーションの設定を変更します")
    @app_commands.describe(
        setting="変更する設定",
        value="新しい値"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_set(
        self,
        interaction: discord.Interaction,
        setting: Literal[
            "スパム保護",
            "メンション制限",
            "招待リンク制限",
            "外部リンク制限",
            "大文字制限",
            "絵文字制限",
            "最大警告回数",
            "警告アクション",
            "タイムアウト期間",
            "ログチャンネル"
        ],
        value: str
    ):
        """自動モデレーションの設定を変更します"""
        try:
            settings = await self.automod_service.get_automod_settings(interaction.guild.id)

            # 設定を更新
            if setting == "スパム保護":
                settings['spam_protection'] = value.lower() == "true"
            elif setting == "メンション制限":
                try:
                    settings['max_mentions'] = int(value)
                except ValueError:
                    await interaction.response.send_message(
                        "無効な値です。数値を指定してください。",
                        ephemeral=True
                    )
                    return
            elif setting == "招待リンク制限":
                settings['block_invites'] = value.lower() == "true"
            elif setting == "外部リンク制限":
                settings['block_links'] = value.lower() == "true"
            elif setting == "大文字制限":
                try:
                    threshold = float(value)
                    if not 0 <= threshold <= 1:
                        raise ValueError
                    settings['caps_threshold'] = threshold
                except ValueError:
                    await interaction.response.send_message(
                        "無効な値です。0から1の間の数値を指定してください。",
                        ephemeral=True
                    )
                    return
            elif setting == "絵文字制限":
                try:
                    settings['max_emojis'] = int(value)
                except ValueError:
                    await interaction.response.send_message(
                        "無効な値です。数値を指定してください。",
                        ephemeral=True
                    )
                    return
            elif setting == "最大警告回数":
                try:
                    settings['max_warnings'] = int(value)
                except ValueError:
                    await interaction.response.send_message(
                        "無効な値です。数値を指定してください。",
                        ephemeral=True
                    )
                    return
            elif setting == "警告アクション":
                if value not in ['kick', 'ban', 'timeout', 'none']:
                    await interaction.response.send_message(
                        "無効な値です。kick, ban, timeout, noneのいずれかを指定してください。",
                        ephemeral=True
                    )
                    return
                settings['action'] = value if value != 'none' else None
            elif setting == "タイムアウト期間":
                try:
                    settings['timeout_duration'] = int(value)
                except ValueError:
                    await interaction.response.send_message(
                        "無効な値です。秒数を指定してください。",
                        ephemeral=True
                    )
                    return
            elif setting == "ログチャンネル":
                try:
                    channel = await commands.TextChannelConverter().convert(interaction, value)
                    settings['log_channel_id'] = channel.id
                except commands.BadArgument:
                    await interaction.response.send_message(
                        "無効なチャンネルです。",
                        ephemeral=True
                    )
                    return

            # 設定を保存
            result = await self.automod_service.update_automod_settings(
                interaction.guild.id,
                settings,
                interaction.user
            )

            await interaction.response.send_message(result)

        except Exception as e:
            await interaction.response.send_message(
                "設定の更新中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to update automod settings: {e}")

    @app_commands.command(name="wordfilter", description="禁止ワードを管理します")
    @app_commands.describe(
        action="実行するアクション",
        word="対象の単語"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def wordfilter(
        self,
        interaction: discord.Interaction,
        action: Literal["追加", "削除", "一覧"],
        word: Optional[str] = None
    ):
        """禁止ワードを管理します"""
        try:
            settings = await self.automod_service.get_automod_settings(interaction.guild.id)
            banned_words = settings.get('banned_words', [])

            if action == "追加":
                if not word:
                    await interaction.response.send_message(
                        "追加する単語を指定してください。",
                        ephemeral=True
                    )
                    return

                if word in banned_words:
                    await interaction.response.send_message(
                        "指定された単語は既に登録されています。",
                        ephemeral=True
                    )
                    return

                banned_words.append(word)
                settings['banned_words'] = banned_words
                await self.automod_service.update_automod_settings(
                    interaction.guild.id,
                    settings,
                    interaction.user
                )

                await interaction.response.send_message(
                    f"禁止ワード「{word}」を追加しました。",
                    ephemeral=True
                )

            elif action == "削除":
                if not word:
                    await interaction.response.send_message(
                        "削除する単語を指定してください。",
                        ephemeral=True
                    )
                    return

                if word not in banned_words:
                    await interaction.response.send_message(
                        "指定された単語は登録されていません。",
                        ephemeral=True
                    )
                    return

                banned_words.remove(word)
                settings['banned_words'] = banned_words
                await self.automod_service.update_automod_settings(
                    interaction.guild.id,
                    settings,
                    interaction.user
                )

                await interaction.response.send_message(
                    f"禁止ワード「{word}」を削除しました。",
                    ephemeral=True
                )

            else:  # 一覧
                if not banned_words:
                    await interaction.response.send_message(
                        "禁止ワードは登録されていません。",
                        ephemeral=True
                    )
                    return

                embed = discord.Embed(
                    title="禁止ワード一覧",
                    color=discord.Color.blue()
                )

                # 25個ずつに分割して表示
                for i in range(0, len(banned_words), 25):
                    chunk = banned_words[i:i+25]
                    embed.add_field(
                        name=f"禁止ワード {i+1}-{i+len(chunk)}",
                        value="\n".join(chunk),
                        inline=False
                    )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                "禁止ワードの管理中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to manage word filter: {e}")

    @automod.error
    @automod_set.error
    @wordfilter.error
    async def automod_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """自動モデレーションコマンドのエラーハンドリング"""
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
            logger.error(f"Error in automod command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(AutoMod(bot)) 