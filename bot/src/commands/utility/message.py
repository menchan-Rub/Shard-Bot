from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, Union
import logging
from datetime import datetime, timedelta
from ...modules.utility.message_service import MessageService

logger = logging.getLogger('utility.message')

class Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_service = MessageService(bot)

    @app_commands.command(name="purge", description="メッセージを一括削除します")
    @app_commands.describe(
        limit="削除する最大メッセージ数",
        user="特定のユーザーのメッセージのみを削除",
        contains="特定の文字列を含むメッセージのみを削除",
        before="この日時より前のメッセージを削除（YYYY-MM-DD HH:MM:SS）",
        after="この日時より後のメッセージを削除（YYYY-MM-DD HH:MM:SS）",
        reason="削除理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        limit: int,
        user: Optional[discord.Member] = None,
        contains: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """
        メッセージを一括削除します。
        """
        try:
            # 日時文字列をdatetimeに変換
            before_dt = None
            after_dt = None
            if before:
                try:
                    before_dt = datetime.strptime(before, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    await interaction.response.send_message(
                        "日時の形式が正しくありません（YYYY-MM-DD HH:MM:SS）",
                        ephemeral=True
                    )
                    return
            if after:
                try:
                    after_dt = datetime.strptime(after, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    await interaction.response.send_message(
                        "日時の形式が正しくありません（YYYY-MM-DD HH:MM:SS）",
                        ephemeral=True
                    )
                    return

            # メッセージを削除
            deleted_count, message = await self.message_service.bulk_delete(
                channel=interaction.channel,
                limit=limit,
                user=user,
                contains=contains,
                before=before_dt,
                after=after_dt,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="メッセージを一括削除しました",
                description=message,
                color=discord.Color.blue()
            )
            embed.add_field(name="削除数", value=str(deleted_count), inline=True)
            if user:
                embed.add_field(name="対象ユーザー", value=user.mention, inline=True)
            if contains:
                embed.add_field(name="検索文字列", value=contains, inline=True)
            if before_dt:
                embed.add_field(name="この日時より前", value=before, inline=True)
            if after_dt:
                embed.add_field(name="この日時より後", value=after, inline=True)
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
                "メッセージの削除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to purge messages: {e}")

    @app_commands.command(name="pin", description="メッセージをピン留めします")
    @app_commands.describe(
        message_id="ピン留めするメッセージのID",
        reason="ピン留めの理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def pin(
        self,
        interaction: discord.Interaction,
        message_id: str,
        reason: Optional[str] = None
    ):
        """
        メッセージをピン留めします。
        """
        try:
            # メッセージを取得
            message = await interaction.channel.fetch_message(int(message_id))
            
            # メッセージをピン留め
            result = await self.message_service.pin_message(
                message=message,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="メッセージをピン留めしました",
                description=result,
                color=discord.Color.blue()
            )
            embed.add_field(name="メッセージ", value=message.content[:1024], inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message(
                "メッセージが見つかりませんでした。",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "メッセージのピン留め中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to pin message: {e}")

    @app_commands.command(name="unpin", description="メッセージのピン留めを解除します")
    @app_commands.describe(
        message_id="ピン留めを解除するメッセージのID",
        reason="解除の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def unpin(
        self,
        interaction: discord.Interaction,
        message_id: str,
        reason: Optional[str] = None
    ):
        """
        メッセージのピン留めを解除します。
        """
        try:
            # メッセージを取得
            message = await interaction.channel.fetch_message(int(message_id))
            
            # ピン留めを解除
            result = await self.message_service.unpin_message(
                message=message,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="メッセージのピン留めを解除しました",
                description=result,
                color=discord.Color.blue()
            )
            embed.add_field(name="メッセージ", value=message.content[:1024], inline=False)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message(
                "メッセージが見つかりませんでした。",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "メッセージのピン留め解除中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to unpin message: {e}")

    @app_commands.command(name="move", description="メッセージを別のチャンネルに移動します")
    @app_commands.describe(
        message_id="移動するメッセージのID",
        destination="移動先のチャンネル",
        reason="移動の理由"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def move(
        self,
        interaction: discord.Interaction,
        message_id: str,
        destination: discord.TextChannel,
        reason: Optional[str] = None
    ):
        """
        メッセージを別のチャンネルに移動します。
        """
        try:
            # メッセージを取得
            message = await interaction.channel.fetch_message(int(message_id))
            
            # メッセージを移動
            result = await self.message_service.move_message(
                message=message,
                destination=destination,
                reason=reason
            )

            # 結果を表示
            embed = discord.Embed(
                title="メッセージを移動しました",
                description=result,
                color=discord.Color.blue()
            )
            embed.add_field(name="移動先", value=destination.mention, inline=True)
            if reason:
                embed.add_field(name="理由", value=reason, inline=False)

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message(
                "メッセージが見つかりませんでした。",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "メッセージの移動中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to move message: {e}")

    @app_commands.command(name="search", description="メッセージを検索します")
    @app_commands.describe(
        query="検索する文字列",
        user="特定のユーザーのメッセージのみを検索",
        limit="検索する最大メッセージ数"
    )
    @app_commands.guild_only()
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        user: Optional[discord.Member] = None,
        limit: Optional[int] = 100
    ):
        """
        メッセージを検索します。
        """
        try:
            # メッセージを検索
            messages = await self.message_service.search_messages(
                channel=interaction.channel,
                query=query,
                user=user,
                limit=limit
            )

            if not messages:
                await interaction.response.send_message(
                    "条件に一致するメッセージが見つかりませんでした。",
                    ephemeral=True
                )
                return

            # 結果を表示
            embed = discord.Embed(
                title="メッセージ検索結果",
                color=discord.Color.blue()
            )
            embed.add_field(name="検索文字列", value=query, inline=True)
            if user:
                embed.add_field(name="対象ユーザー", value=user.mention, inline=True)
            embed.add_field(name="検索結果数", value=str(len(messages)), inline=True)

            # メッセージを表示（最大10件）
            for i, message in enumerate(messages[:10], 1):
                embed.add_field(
                    name=f"#{i} - {message.author.display_name} ({message.created_at.strftime('%Y-%m-%d %H:%M:%S')})",
                    value=message.content[:1024],
                    inline=False
                )

            if len(messages) > 10:
                embed.set_footer(text="最初の10件のみ表示しています。")

            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "メッセージの検索中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to search messages: {e}")

    @app_commands.command(name="history", description="メッセージの編集履歴を表示します")
    @app_commands.describe(
        message_id="履歴を表示するメッセージのID"
    )
    @app_commands.guild_only()
    async def history(
        self,
        interaction: discord.Interaction,
        message_id: str
    ):
        """
        メッセージの編集履歴を表示します。
        """
        try:
            # メッセージを取得
            message = await interaction.channel.fetch_message(int(message_id))
            
            # 編集履歴を取得
            history = await self.message_service.get_message_history(message)

            if not history:
                await interaction.response.send_message(
                    "編集履歴が見つかりませんでした。",
                    ephemeral=True
                )
                return

            # 結果を表示
            embed = discord.Embed(
                title="メッセージ編集履歴",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="現在の内容",
                value=message.content[:1024],
                inline=False
            )

            # 編集履歴を表示
            for i, edit in enumerate(history, 1):
                editor = interaction.guild.get_member(edit['editor'])
                editor_name = editor.display_name if editor else "不明"
                embed.add_field(
                    name=f"編集 #{i} - {editor_name} ({edit['timestamp'].strftime('%Y-%m-%d %H:%M:%S')})",
                    value=edit['content'][:1024],
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except discord.NotFound:
            await interaction.response.send_message(
                "メッセージが見つかりませんでした。",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(
                f"エラー: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "編集履歴の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get message history: {e}")

    @purge.error
    @pin.error
    @unpin.error
    @move.error
    async def message_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """メッセージコマンドのエラーハンドリング"""
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
            logger.error(f"Error in message command: {error}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Message(bot)) 