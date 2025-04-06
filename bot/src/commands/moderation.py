import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, ModerationAction, UserInfraction
from bot.src.modules.utility.embed_builder import EmbedBuilder
from bot.src.utils.permissions import has_mod_permissions, has_admin_permissions
from bot.src.modules.moderation.infractions import InfractionManager

class ConfirmActionView(discord.ui.View):
    """モデレーションアクションを確認するためのビュー"""
    
    def __init__(self, bot: commands.Bot, mod_user: discord.Member, target_user: discord.Member, 
                 action_type: str, reason: str, duration: Optional[int] = None, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mod_user = mod_user
        self.target_user = target_user
        self.action_type = action_type
        self.reason = reason
        self.duration = duration
        self.logger = logging.getLogger('bot.commands.moderation.confirm')
        
    async def on_timeout(self):
        """タイムアウト時の処理"""
        try:
            # ボタンを無効化
            for item in self.children:
                item.disabled = True
            
            # メッセージを更新して無効化を反映
            await self.message.edit(view=self)
            
            # タイムアウトメッセージを追加
            embed = self.message.embeds[0]
            embed.add_field(name="⏰ タイムアウト", value="操作がタイムアウトしました。再度コマンドを実行してください。", inline=False)
            await self.message.edit(embed=embed)
        except Exception as e:
            self.logger.error(f"タイムアウト処理中にエラーが発生しました: {e}")
    
    @discord.ui.button(label="確認", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """確認ボタンのコールバック"""
        # 権限チェック - コマンド実行者以外は押せない
        if interaction.user.id != self.mod_user.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみが使用できます。", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        
        try:
            # インフラクションマネージャーを使用してアクションを実行
            infraction_manager = InfractionManager(self.bot)
            
            # アクションの種類に応じて処理を分岐
            if self.action_type == "warn":
                infraction_id = await infraction_manager.warn_user(
                    self.target_user.guild.id, 
                    self.mod_user.id, 
                    self.target_user.id, 
                    self.reason
                )
                success_message = f"{self.target_user.mention} に警告を与えました"
                
            elif self.action_type == "mute":
                infraction_id = await infraction_manager.mute_user(
                    self.target_user.guild.id, 
                    self.mod_user.id, 
                    self.target_user.id, 
                    self.reason,
                    self.duration or 60  # デフォルトは60分
                )
                duration_text = f"（{self.duration}分間）" if self.duration else ""
                success_message = f"{self.target_user.mention} をミュートしました{duration_text}"
                
            elif self.action_type == "kick":
                infraction_id = await infraction_manager.kick_user(
                    self.target_user.guild.id, 
                    self.mod_user.id, 
                    self.target_user.id, 
                    self.reason
                )
                success_message = f"{self.target_user.mention} をサーバーからキックしました"
                
            elif self.action_type == "ban":
                infraction_id = await infraction_manager.ban_user(
                    self.target_user.guild.id, 
                    self.mod_user.id, 
                    self.target_user.id, 
                    self.reason,
                    delete_message_days=1
                )
                success_message = f"{self.target_user.mention} をサーバーからBANしました"
                
            else:
                raise ValueError(f"不明なアクションタイプ: {self.action_type}")
            
            # 成功メッセージを更新
            embed = self.message.embeds[0]
            embed.add_field(name="✅ 成功", value=success_message, inline=False)
            embed.add_field(name="📝 違反ID", value=f"`{infraction_id}`", inline=False)
            await self.message.edit(embed=embed, view=self)
            
            # 確認メッセージを送信
            await interaction.followup.send(f"✅ {success_message}", ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"モデレーションアクション実行中にエラーが発生しました: {e}")
            
            # エラーメッセージを更新
            embed = self.message.embeds[0]
            embed.add_field(name="❌ エラー", value=f"アクション実行中にエラーが発生しました: {e}", inline=False)
            await self.message.edit(embed=embed, view=self)
            
            # エラーメッセージを送信
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """キャンセルボタンのコールバック"""
        # 権限チェック - コマンド実行者以外は押せない
        if interaction.user.id != self.mod_user.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみが使用できます。", ephemeral=True)
            return
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        
        # メッセージを更新
        embed = self.message.embeds[0]
        embed.add_field(name="❌ キャンセル", value="アクションはキャンセルされました。", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


class UserInfractionsView(discord.ui.View):
    """ユーザーの違反履歴を表示するビュー"""
    
    def __init__(self, bot: commands.Bot, mod_user: discord.Member, target_user: discord.Member, 
                 infractions: List[Dict[str, Any]], page: int = 0, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mod_user = mod_user
        self.target_user = target_user
        self.infractions = infractions
        self.page = page
        self.max_page = max(0, (len(infractions) - 1) // 5)  # 1ページに5件表示
        self.logger = logging.getLogger('bot.commands.moderation.history')
        
        # ページネーションボタンの状態を更新
        self.update_buttons()
    
    def update_buttons(self):
        """ページネーションボタンの状態を更新"""
        # 前のページボタン
        self.previous_page_button.disabled = (self.page <= 0)
        
        # 次のページボタン
        self.next_page_button.disabled = (self.page >= self.max_page)
    
    async def update_message(self, interaction: discord.Interaction):
        """メッセージを更新してページに対応する違反履歴を表示"""
        # 現在のページの違反を取得
        start_idx = self.page * 5
        end_idx = min(start_idx + 5, len(self.infractions))
        current_infractions = self.infractions[start_idx:end_idx]
        
        # 埋め込みを作成
        embed = EmbedBuilder.create_embed(
            title=f"📋 {self.target_user.display_name} の違反履歴",
            description=f"{self.target_user.mention} の違反履歴を表示しています。",
            color=discord.Color.blue(),
            thumbnail=self.target_user.display_avatar.url
        )
        
        # ページ情報の追加
        embed.set_footer(text=f"ページ {self.page + 1}/{self.max_page + 1} • 合計 {len(self.infractions)} 件")
        
        # 違反がない場合
        if not current_infractions:
            embed.add_field(name="情報", value="違反履歴はありません。", inline=False)
        
        # 違反を追加
        for infraction in current_infractions:
            infraction_id = infraction.get("id", "不明")
            action_type = infraction.get("action_type", "不明")
            reason = infraction.get("reason", "理由なし")
            created_at = infraction.get("created_at", datetime.now())
            mod_id = infraction.get("moderator_id", 0)
            
            # アクションタイプに応じたエモジ
            emoji = "⚠️"
            if action_type == "mute":
                emoji = "🔇"
            elif action_type == "kick":
                emoji = "👢"
            elif action_type == "ban":
                emoji = "🔨"
            
            # フィールド名と値の作成
            field_name = f"{emoji} {action_type.capitalize()} (ID: {infraction_id})"
            field_value = f"**理由:** {reason}\n"
            field_value += f"**日時:** {created_at.strftime('%Y-%m-%d %H:%M')}\n"
            field_value += f"**モデレーター:** <@{mod_id}>"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        # メッセージを更新
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="前のページ", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="previous_page")
    async def previous_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """前のページボタンのコールバック"""
        # 権限チェック - コマンド実行者以外は押せない
        if interaction.user.id != self.mod_user.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみが使用できます。", ephemeral=True)
            return
        
        # ページを減らす
        self.page = max(0, self.page - 1)
        
        # ボタン状態を更新
        self.update_buttons()
        
        # メッセージを更新
        await self.update_message(interaction)
    
    @discord.ui.button(label="次のページ", style=discord.ButtonStyle.secondary, emoji="▶️", custom_id="next_page")
    async def next_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """次のページボタンのコールバック"""
        # 権限チェック - コマンド実行者以外は押せない
        if interaction.user.id != self.mod_user.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみが使用できます。", ephemeral=True)
            return
        
        # ページを増やす
        self.page = min(self.max_page, self.page + 1)
        
        # ボタン状態を更新
        self.update_buttons()
        
        # メッセージを更新
        await self.update_message(interaction)
    
    @discord.ui.button(label="閉じる", style=discord.ButtonStyle.danger, emoji="❌", custom_id="close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """閉じるボタンのコールバック"""
        # 権限チェック - コマンド実行者以外は押せない
        if interaction.user.id != self.mod_user.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみが使用できます。", ephemeral=True)
            return
        
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        
        # メッセージを更新
        embed = interaction.message.embeds[0]
        await interaction.response.edit_message(embed=embed, view=self)


class Moderation(commands.Cog):
    """モデレーションコマンドの実装"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('bot.commands.moderation')
        self.infraction_manager = InfractionManager(bot)
    
    @app_commands.command(name="warn", description="ユーザーに警告を与えます")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(
        user="警告を与えるユーザー",
        reason="警告の理由"
    )
    async def warn_command(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """ユーザー警告コマンド"""
        # 権限チェック
        if not has_mod_permissions(interaction.user, interaction.guild):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドはモデレーター以上の権限が必要です。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 自分自身への警告はできない
        if user.id == interaction.user.id:
            await interaction.response.send_message("⚠️ 自分自身に警告を与えることはできません。", ephemeral=True)
            return
        
        # BOTへの警告はできない
        if user.bot:
            await interaction.response.send_message("⚠️ BOTに警告を与えることはできません。", ephemeral=True)
            return
        
        # サーバーオーナーへの警告はできない
        if user.id == interaction.guild.owner_id:
            await interaction.response.send_message("⚠️ サーバーオーナーに警告を与えることはできません。", ephemeral=True)
            return
        
        # 権限階層チェック
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "⚠️ 自分と同じまたはそれ以上の権限を持つユーザーに警告を与えることはできません。", 
                ephemeral=True
            )
            return
        
        # 確認メッセージを表示
        embed = EmbedBuilder.create_embed(
            title="⚠️ ユーザー警告の確認",
            description=f"{user.mention} に警告を与えようとしています。",
            color=discord.Color.yellow(),
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": "ユーザー", "value": f"{user} (`{user.id}`)", "inline": True},
                {"name": "モデレーター", "value": f"{interaction.user} (`{interaction.user.id}`)", "inline": True},
                {"name": "理由", "value": reason, "inline": False},
            ]
        )
        
        # 確認ビューを送信
        view = ConfirmActionView(self.bot, interaction.user, user, "warn", reason)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # ビューにメッセージを保存
        message = await interaction.original_response()
        view.message = message
    
    @app_commands.command(name="mute", description="ユーザーをミュートします")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(
        user="ミュートするユーザー",
        duration="ミュート期間（分）",
        reason="ミュートの理由"
    )
    async def mute_command(self, interaction: discord.Interaction, user: discord.Member, 
                          duration: Optional[int] = 60, reason: Optional[str] = "理由なし"):
        """ユーザーミュートコマンド"""
        # 権限チェック
        if not has_mod_permissions(interaction.user, interaction.guild):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドはモデレーター以上の権限が必要です。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 自分自身へのミュートはできない
        if user.id == interaction.user.id:
            await interaction.response.send_message("⚠️ 自分自身をミュートすることはできません。", ephemeral=True)
            return
        
        # BOTへのミュートはできない
        if user.bot:
            await interaction.response.send_message("⚠️ BOTをミュートすることはできません。", ephemeral=True)
            return
        
        # サーバーオーナーへのミュートはできない
        if user.id == interaction.guild.owner_id:
            await interaction.response.send_message("⚠️ サーバーオーナーをミュートすることはできません。", ephemeral=True)
            return
        
        # 権限階層チェック
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "⚠️ 自分と同じまたはそれ以上の権限を持つユーザーをミュートすることはできません。", 
                ephemeral=True
            )
            return
        
        # ミュート期間の範囲チェック
        if duration < 1:
            await interaction.response.send_message("⚠️ ミュート期間は1分以上である必要があります。", ephemeral=True)
            return
        if duration > 40320:  # 28日（Discordの制限）
            await interaction.response.send_message("⚠️ ミュート期間は最大28日（40320分）までです。", ephemeral=True)
            return
        
        # 終了時間を計算
        end_time = datetime.now() + timedelta(minutes=duration)
        
        # 確認メッセージを表示
        embed = EmbedBuilder.create_embed(
            title="🔇 ユーザーミュートの確認",
            description=f"{user.mention} をミュートしようとしています。",
            color=discord.Color.orange(),
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": "ユーザー", "value": f"{user} (`{user.id}`)", "inline": True},
                {"name": "モデレーター", "value": f"{interaction.user} (`{interaction.user.id}`)", "inline": True},
                {"name": "期間", "value": f"{duration}分（{end_time.strftime('%Y-%m-%d %H:%M')}まで）", "inline": True},
                {"name": "理由", "value": reason, "inline": False},
            ]
        )
        
        # 確認ビューを送信
        view = ConfirmActionView(self.bot, interaction.user, user, "mute", reason, duration)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # ビューにメッセージを保存
        message = await interaction.original_response()
        view.message = message
    
    @app_commands.command(name="kick", description="ユーザーをサーバーからキックします")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(
        user="キックするユーザー",
        reason="キックの理由"
    )
    async def kick_command(self, interaction: discord.Interaction, user: discord.Member, 
                          reason: Optional[str] = "理由なし"):
        """ユーザーキックコマンド"""
        # 権限チェック
        if not has_mod_permissions(interaction.user, interaction.guild, kick=True):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドはキック権限が必要です。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 自分自身へのキックはできない
        if user.id == interaction.user.id:
            await interaction.response.send_message("⚠️ 自分自身をキックすることはできません。", ephemeral=True)
            return
        
        # BOTへのキックはできない
        if user.bot:
            await interaction.response.send_message("⚠️ BOTをキックすることはできません。", ephemeral=True)
            return
        
        # サーバーオーナーへのキックはできない
        if user.id == interaction.guild.owner_id:
            await interaction.response.send_message("⚠️ サーバーオーナーをキックすることはできません。", ephemeral=True)
            return
        
        # 権限階層チェック
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "⚠️ 自分と同じまたはそれ以上の権限を持つユーザーをキックすることはできません。", 
                ephemeral=True
            )
            return
        
        # 確認メッセージを表示
        embed = EmbedBuilder.create_embed(
            title="👢 ユーザーキックの確認",
            description=f"{user.mention} をサーバーからキックしようとしています。",
            color=discord.Color.red(),
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": "ユーザー", "value": f"{user} (`{user.id}`)", "inline": True},
                {"name": "モデレーター", "value": f"{interaction.user} (`{interaction.user.id}`)", "inline": True},
                {"name": "理由", "value": reason, "inline": False},
            ]
        )
        
        # 確認ビューを送信
        view = ConfirmActionView(self.bot, interaction.user, user, "kick", reason)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # ビューにメッセージを保存
        message = await interaction.original_response()
        view.message = message
    
    @app_commands.command(name="ban", description="ユーザーをサーバーからBANします")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(
        user="BANするユーザー",
        reason="BANの理由"
    )
    async def ban_command(self, interaction: discord.Interaction, user: discord.Member, 
                          reason: Optional[str] = "理由なし"):
        """ユーザーBANコマンド"""
        # 権限チェック
        if not has_mod_permissions(interaction.user, interaction.guild, ban=True):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドはBAN権限が必要です。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 自分自身へのBANはできない
        if user.id == interaction.user.id:
            await interaction.response.send_message("⚠️ 自分自身をBANすることはできません。", ephemeral=True)
            return
        
        # BOTへのBANはできない
        if user.bot:
            await interaction.response.send_message("⚠️ BOTをBANすることはできません。", ephemeral=True)
            return
        
        # サーバーオーナーへのBANはできない
        if user.id == interaction.guild.owner_id:
            await interaction.response.send_message("⚠️ サーバーオーナーをBANすることはできません。", ephemeral=True)
            return
        
        # 権限階層チェック
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "⚠️ 自分と同じまたはそれ以上の権限を持つユーザーをBANすることはできません。", 
                ephemeral=True
            )
            return
        
        # 確認メッセージを表示
        embed = EmbedBuilder.create_embed(
            title="🔨 ユーザーBANの確認",
            description=f"{user.mention} をサーバーからBANしようとしています。",
            color=discord.Color.dark_red(),
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": "ユーザー", "value": f"{user} (`{user.id}`)", "inline": True},
                {"name": "モデレーター", "value": f"{interaction.user} (`{interaction.user.id}`)", "inline": True},
                {"name": "理由", "value": reason, "inline": False},
            ]
        )
        
        # 確認ビューを送信
        view = ConfirmActionView(self.bot, interaction.user, user, "ban", reason)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # ビューにメッセージを保存
        message = await interaction.original_response()
        view.message = message
    
    @app_commands.command(name="history", description="ユーザーの違反履歴を表示します")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="履歴を確認するユーザー")
    async def history_command(self, interaction: discord.Interaction, user: discord.Member):
        """ユーザー違反履歴コマンド"""
        # 権限チェック
        if not has_mod_permissions(interaction.user, interaction.guild):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドはモデレーター以上の権限が必要です。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 違反履歴を取得（仮実装）
            # 実際の実装では、InfractionManagerからユーザーの違反履歴を取得する
            await asyncio.sleep(1)  # 実際のDB取得処理の代わりに遅延
            
            # サンプルデータ（実際はデータベースから取得）
            infractions = [
                {
                    "id": "INF001",
                    "action_type": "warn",
                    "reason": "チャット内での不適切な言葉づかい",
                    "created_at": datetime.now() - timedelta(days=7),
                    "moderator_id": interaction.user.id
                },
                {
                    "id": "INF002",
                    "action_type": "mute",
                    "reason": "スパム行為",
                    "created_at": datetime.now() - timedelta(days=5),
                    "moderator_id": interaction.user.id
                },
                {
                    "id": "INF003",
                    "action_type": "warn",
                    "reason": "宣伝リンクの投稿",
                    "created_at": datetime.now() - timedelta(days=3),
                    "moderator_id": interaction.user.id
                }
            ]
            
            # 違反履歴がない場合
            if not infractions:
                embed = EmbedBuilder.create_embed(
                    title=f"📋 {user.display_name} の違反履歴",
                    description=f"{user.mention} の違反履歴を表示しています。",
                    color=discord.Color.blue(),
                    thumbnail=user.display_avatar.url,
                    fields=[
                        {"name": "情報", "value": "違反履歴はありません。", "inline": False}
                    ]
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 違反履歴ビューを送信
            view = UserInfractionsView(self.bot, interaction.user, user, infractions)
            
            # 最初のページの埋め込みを作成
            embed = EmbedBuilder.create_embed(
                title=f"📋 {user.display_name} の違反履歴",
                description=f"{user.mention} の違反履歴を表示しています。",
                color=discord.Color.blue(),
                thumbnail=user.display_avatar.url
            )
            
            # ページ情報の追加
            embed.set_footer(text=f"ページ 1/{view.max_page + 1} • 合計 {len(infractions)} 件")
            
            # 最初のページの違反を追加
            for infraction in infractions[:5]:
                infraction_id = infraction.get("id", "不明")
                action_type = infraction.get("action_type", "不明")
                reason = infraction.get("reason", "理由なし")
                created_at = infraction.get("created_at", datetime.now())
                mod_id = infraction.get("moderator_id", 0)
                
                # アクションタイプに応じたエモジ
                emoji = "⚠️"
                if action_type == "mute":
                    emoji = "🔇"
                elif action_type == "kick":
                    emoji = "👢"
                elif action_type == "ban":
                    emoji = "🔨"
                
                # フィールド名と値の作成
                field_name = f"{emoji} {action_type.capitalize()} (ID: {infraction_id})"
                field_value = f"**理由:** {reason}\n"
                field_value += f"**日時:** {created_at.strftime('%Y-%m-%d %H:%M')}\n"
                field_value += f"**モデレーター:** <@{mod_id}>"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
            
            # ビューを送信
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # ビューにメッセージを保存
            message = await interaction.original_response()
            view.message = message
            
        except Exception as e:
            self.logger.error(f"違反履歴取得中にエラーが発生しました: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    """Cogをボットに追加"""
    await bot.add_cog(Moderation(bot)) 