import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional
import time

logger = logging.getLogger('ShardBot.Events.Moderation')

class ModerationEvents(commands.Cog):
    """モデレーション機能に関連するイベントを処理するコグ"""
    
    def __init__(self, bot):
        self.bot = bot
        self.moderation = None
        self.ready = asyncio.Event()
        self.bot.loop.create_task(self._setup())
    
    async def _setup(self):
        """モデレーションマネージャーを初期化"""
        try:
            await self.bot.wait_until_ready()
            # bot.moderationが初期化されるまで待機（最大30秒）
            for _ in range(30):  # 30秒のタイムアウト
                if hasattr(self.bot, 'moderation') and self.bot.moderation is not None:
                    self.moderation = self.bot.moderation
                    self.ready.set()
                    logger.info("Moderation events initialized")
                    break
                await asyncio.sleep(1)
            else:
                logger.warning("Moderation manager initialization timed out")
        except Exception as e:
            logger.error(f"Error in moderation events setup: {e}")
            self.ready.set()  # エラーが発生しても準備完了とマーク
    
    async def cog_before_invoke(self, ctx):
        """コマンド実行前に初期化完了を待機"""
        await self.ready.wait()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージ送信イベントを処理"""
        await self.ready.wait()  # 初期化完了を待機
        
        if not self.moderation or message.author.id == self.bot.user.id:
            return
        
        try:
            await self.moderation.process_message(message)
        except Exception as e:
            logger.error(f"Error processing message in moderation: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバー参加イベントを処理"""
        await self.ready.wait()  # 初期化完了を待機
        
        if not self.moderation:
            return
        
        try:
            await self.moderation.process_member_join(member)
        except Exception as e:
            logger.error(f"Error processing member join in moderation: {e}")
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """チャンネル作成イベントを処理（レイド中は自動的に権限を制限）"""
        await self.ready.wait()  # 初期化完了を待機
        
        if not self.moderation or not isinstance(channel, discord.TextChannel):
            return
        
        try:
            guild_id = str(channel.guild.id)
            
            # レイドモードがアクティブな場合、新しいチャンネルに制限を適用
            if self.moderation.is_raid_active(guild_id):
                # @everyoneの権限を制限
                everyone = channel.guild.default_role
                await channel.set_permissions(
                    everyone,
                    send_messages=False,
                    add_reactions=False,
                    reason="レイド保護: 新規チャンネルを自動的に制限"
                )
                
                logger.info(f"Applied raid protection permissions to new channel {channel.name} in {channel.guild.name}")
        except Exception as e:
            logger.error(f"Error handling channel create event: {e}")
    
    @commands.command(name="raidmode")
    @commands.has_permissions(administrator=True)
    async def raidmode_command(self, ctx: commands.Context, action: str = "status"):
        """レイド保護モードを管理するコマンド
        
        使用方法:
        !raidmode status - 現在のレイドモードのステータスを表示
        !raidmode end - レイド保護モードを終了
        """
        if not self.moderation:
            await ctx.send("モデレーションシステムが初期化されていません。")
            return
        
        guild_id = str(ctx.guild.id)
        
        if action.lower() == "status":
            if self.moderation.is_raid_active(guild_id):
                raid_info = self.moderation.get_raid_info(guild_id)
                if raid_info:
                    duration = int(raid_info['duration'] / 60)  # 分に変換
                    await ctx.send(
                        f"⚠️ **レイド警戒モードがアクティブです** ⚠️\n"
                        f"• 検出された参加者数: {raid_info['count']}人\n"
                        f"• アクティブ時間: {duration}分\n"
                        f"• レイドモードを終了するには `!raidmode end` を使用してください。"
                    )
                else:
                    await ctx.send("⚠️ レイド警戒モードがアクティブですが、詳細情報を取得できませんでした。")
            else:
                await ctx.send("✅ レイド警戒モードは現在アクティブではありません。")
        
        elif action.lower() == "end":
            if self.moderation.is_raid_active(guild_id):
                success = await self.moderation.end_raid_mode(guild_id)
                if success:
                    await ctx.send("✅ レイド警戒モードを終了しました。通常の操作に戻ります。")
                else:
                    await ctx.send("❌ レイド警戒モードの終了に失敗しました。")
            else:
                await ctx.send("ℹ️ レイド警戒モードは現在アクティブではありません。")
        
        else:
            await ctx.send(
                "❌ 無効なコマンドです。以下のコマンドが使用可能です:\n"
                "• `!raidmode status` - 現在のレイドモードのステータスを表示\n"
                "• `!raidmode end` - レイド保護モードを終了"
            )
    
    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge_command(self, ctx: commands.Context, amount: int = 10):
        """指定した数のメッセージを一括削除するコマンド
        
        使用方法:
        !purge [数量=10] - 指定した数のメッセージを削除（デフォルト: 10）
        """
        if amount <= 0 or amount > 100:
            await ctx.send("❌ 削除するメッセージ数は1〜100の間で指定してください。")
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # コマンド自体も含める
            msg = await ctx.send(f"✅ {len(deleted) - 1}件のメッセージを削除しました。")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            logger.error(f"Error in purge command: {e}")
            await ctx.send(f"❌ メッセージの削除中にエラーが発生しました: {e}")

async def setup(bot):
    """Cogを登録"""
    try:
        await bot.add_cog(ModerationEvents(bot))
        return True
    except Exception as e:
        logger.error(f"ModerationEventsの登録に失敗しました: {e}")
        return True  # エラーが発生しても明示的にTrueを返す 