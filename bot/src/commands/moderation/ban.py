from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional
import logging
import datetime

from bot.src.db.database import get_db_session
from bot.src.db.models import AuditLog
from bot.src.utils.permissions import is_moderator

logger = logging.getLogger('moderation.ban')

class Ban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="指定したユーザーをBANします")
    @app_commands.describe(
        member="BANするユーザー",
        reason="BANの理由",
        delete_message_days="削除するメッセージの日数（0-7）",
        silent="BANの通知をユーザーに送信するかどうか",
        dm_message="ユーザーに送信するカスタムDMメッセージ"
    )
    @app_commands.guild_only()
    @is_moderator()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = "理由が指定されていません",
        delete_message_days: Optional[int] = 1,
        silent: Optional[bool] = False,
        dm_message: Optional[str] = None
    ):
        """
        指定したユーザーをBANします。
        
        Parameters
        ----------
        member : discord.Member
            BANするユーザー
        reason : str, optional
            BANの理由
        delete_message_days : int, optional
            削除するメッセージの日数（0-7）
        silent : bool, optional
            True の場合、BANをサイレントに実行（結果を公開チャンネルに投稿しない）
        dm_message : str, optional
            ユーザーに送信するカスタムDMメッセージ
        """
        # 応答を遅延
        await interaction.response.defer(ephemeral=silent)
        
        # 権限チェック
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.followup.send(
                "⚠️ 自分より上位のロールを持つユーザーをBANすることはできません。",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send(
                "⚠️ BOTより上位のロールを持つユーザーをBANすることはできません。",
                ephemeral=True
            )
            return
            
        if member.id == interaction.guild.owner_id:
            await interaction.followup.send(
                "⚠️ サーバーオーナーをBANすることはできません。",
                ephemeral=True
            )
            return

        # メッセージ削除日数の制限
        delete_message_days = max(0, min(delete_message_days, 7))

        try:
            # DMを送信（silent=Falseまたはdm_messageが指定されている場合）
            dm_sent = False
            if not silent or dm_message:
                try:
                    # DMの内容
                    embed = discord.Embed(
                        title=f"{interaction.guild.name} からBANされました",
                        description=dm_message or f"理由: {reason}",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                    embed.add_field(name="モデレーター", value=interaction.user.name, inline=True)
                    
                    await member.send(embed=embed)
                    dm_sent = True
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.warning(f"Failed to send DM to {member} (ID: {member.id}): {e}")
            
            # BANを実行
            full_reason = f"{reason} (モデレーター: {interaction.user.name}#{interaction.user.discriminator}, ID: {interaction.user.id})"
            await member.ban(
                reason=full_reason,
                delete_message_days=delete_message_days
            )

            # データベースに記録
            async for session in get_db_session():
                try:
                    # 監査ログを作成
                    audit_log = AuditLog(
                        guild_id=interaction.guild.id,
                        action_type="ban",
                        user_id=interaction.user.id,
                        target_id=member.id,
                        reason=reason,
                        details={
                            "delete_message_days": delete_message_days,
                            "dm_sent": dm_sent,
                            "silent": silent
                        }
                    )
                    session.add(audit_log)
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(f"データベースへの記録中にエラーが発生しました: {e}")

            # 成功メッセージを送信
            embed = discord.Embed(
                title="🔨 ユーザーをBANしました",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="対象ユーザー", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            embed.add_field(name="モデレーター", value=interaction.user.mention, inline=True)
            embed.add_field(name="DMの送信", value="成功" if dm_sent else "失敗/未送信", inline=True)
            embed.set_footer(text=f"メッセージ削除: {delete_message_days}日分")

            await interaction.followup.send(embed=embed)

            # モデレーションログチャンネルにも記録（silent=Trueの場合でも）
            try:
                # ログチャンネルのIDを取得
                async for session in get_db_session():
                    result = await session.execute(
                        "SELECT log_channel_id FROM guild_settings WHERE guild_id = :guild_id",
                        {"guild_id": interaction.guild.id}
                    )
                    log_channel_id = result.scalar_one_or_none()
                    
                    if log_channel_id:
                        log_channel = interaction.guild.get_channel(log_channel_id)
                        if log_channel and isinstance(log_channel, discord.TextChannel):
                            await log_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"ログチャンネルへの送信中にエラーが発生しました: {e}")

        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ BANの権限がありません。ボットに必要な権限が付与されているか確認してください。",
                ephemeral=True
            )
            logger.error(f"Failed to ban user {member.id} in guild {interaction.guild.id}: Forbidden")

        except discord.HTTPException as e:
            await interaction.followup.send(
                f"⚠️ BANの実行中にDiscord APIエラーが発生しました: {e}",
                ephemeral=True
            )
            logger.error(f"Failed to ban user {member.id} in guild {interaction.guild.id}: {e}")

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ BANの実行中に予期せぬエラーが発生しました: {type(e).__name__}",
                ephemeral=True
            )
            logger.error(f"Failed to ban user {member.id} in guild {interaction.guild.id}: {e}", exc_info=True)

    @ban.error
    async def ban_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """BANコマンドのエラーハンドリング"""
        if interaction.response.is_done():
            send = interaction.followup.send
        else:
            send = interaction.response.send_message
            
        if isinstance(error, app_commands.CheckFailure):
            await send(
                "⚠️ このコマンドを実行する権限がありません。モデレーター以上の権限が必要です。",
                ephemeral=True
            )
        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.Forbidden):
                await send(
                    "⚠️ BOTに必要な権限がありません。BANの権限を付与してください。",
                    ephemeral=True
                )
            else:
                await send(
                    f"⚠️ コマンドの実行中にエラーが発生しました: {original.__class__.__name__}",
                    ephemeral=True
                )
                logger.error(f"Error in ban command: {error}", exc_info=True)
        else:
            await send(
                "⚠️ コマンドの実行中に不明なエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Unknown error in ban command: {error}", exc_info=True)

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Ban(bot)) 