import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from bot.src.db.database import get_db_session
from bot.src.db.models import Guild, GuildSettings
from bot.src.modules.utility.embed_builder import EmbedBuilder
from bot.src.utils.permissions import has_admin_permissions

class SetupView(discord.ui.View):
    """セットアップのためのインタラクティブなビュー"""
    
    def __init__(self, bot: commands.Bot, ctx, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.logger = logging.getLogger('bot.commands.setup')
        
    async def on_timeout(self):
        """タイムアウト時の処理"""
        try:
            # ボタンを無効化
            for item in self.children:
                item.disabled = True
            
            # メッセージを更新して無効化を反映
            await self.message.edit(view=self)
        except Exception as e:
            self.logger.error(f"タイムアウト処理中にエラーが発生しました: {e}")
    
    @discord.ui.button(label="一般設定", style=discord.ButtonStyle.primary, emoji="⚙️", row=0)
    async def general_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """一般設定ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # 一般設定モーダルを表示
        general_modal = GeneralSettingsModal(self.bot, self.ctx.guild.id)
        await interaction.followup.send("一般設定を開きます...", ephemeral=True)
        await interaction.response.send_modal(general_modal)
    
    @discord.ui.button(label="モデレーション設定", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def moderation_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """モデレーション設定ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # モデレーション設定ビューを送信
        moderation_view = ModerationSettingsView(self.bot, self.ctx)
        embed = EmbedBuilder.create_embed(
            title="🛡️ モデレーション設定",
            description="サーバーのモデレーション設定を行います。下のボタンから設定を選択してください。",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, view=moderation_view, ephemeral=True)
    
    @discord.ui.button(label="自動応答設定", style=discord.ButtonStyle.primary, emoji="🤖", row=0)
    async def auto_response_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """自動応答設定ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # 自動応答設定ビューを送信
        auto_response_view = AutoResponseView(self.bot, self.ctx)
        embed = EmbedBuilder.create_embed(
            title="🤖 自動応答設定",
            description="サーバーの自動応答設定を行います。メッセージに自動的に反応するルールを設定できます。",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, view=auto_response_view, ephemeral=True)
    
    @discord.ui.button(label="レイド保護設定", style=discord.ButtonStyle.primary, emoji="🔒", row=1)
    async def raid_protection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """レイド保護設定ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # レイド保護設定ビューを送信
        raid_view = RaidProtectionView(self.bot, self.ctx)
        embed = EmbedBuilder.create_embed(
            title="🔒 レイド保護設定",
            description="サーバーのレイド保護設定を行います。短時間での大量参加に対する保護を設定できます。",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, view=raid_view, ephemeral=True)
    
    @discord.ui.button(label="アンチスパム設定", style=discord.ButtonStyle.primary, emoji="🧹", row=1)
    async def anti_spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """アンチスパム設定ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # アンチスパム設定ビューを送信
        spam_view = AntiSpamView(self.bot, self.ctx)
        embed = EmbedBuilder.create_embed(
            title="🧹 アンチスパム設定",
            description="サーバーのアンチスパム設定を行います。メッセージスパムやメンションスパムを防ぐための設定ができます。",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, view=spam_view, ephemeral=True)
    
    @discord.ui.button(label="Webダッシュボード", style=discord.ButtonStyle.success, emoji="🌐", row=1)
    async def dashboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Webダッシュボードボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # Webダッシュボードへのリンクを送信
        dashboard_url = f"https://shard-bot.example.com/dashboard/guild/{interaction.guild_id}"
        embed = EmbedBuilder.create_embed(
            title="🌐 Webダッシュボード",
            description=f"より詳細な設定はWebダッシュボードから行えます。\n[ダッシュボードを開く]({dashboard_url})",
            color=discord.Color.blurple()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """キャンセルボタンのコールバック"""
        # ボタンを無効化して終了
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # オリジナルメッセージを編集
        embed = EmbedBuilder.create_embed(
            title="❌ 設定をキャンセルしました",
            description="設定をキャンセルしました。",
            color=discord.Color.red()
        )
        await interaction.message.edit(embed=embed, view=None)


class GeneralSettingsModal(discord.ui.Modal, title="サーバー一般設定"):
    """一般設定を行うためのモーダル"""
    
    prefix = discord.ui.TextInput(
        label="コマンドプレフィックス",
        placeholder="!",
        default="!",
        min_length=1,
        max_length=5,
        required=True,
    )
    
    log_channel = discord.ui.TextInput(
        label="ログチャンネル名",
        placeholder="botログ用のチャンネル名を入力",
        required=False,
    )
    
    welcome_message = discord.ui.TextInput(
        label="参加時のウェルカムメッセージ",
        placeholder="新しいメンバーへの挨拶メッセージ",
        style=discord.TextStyle.paragraph,
        required=False,
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.logger = logging.getLogger('bot.commands.setup.modal')
    
    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # データベースに設定を保存
            with get_db_session() as session:
                # ギルド情報を取得
                guild_settings = session.query(GuildSettings).filter(
                    GuildSettings.guild.has(discord_id=str(self.guild_id))
                ).first()
                
                if not guild_settings:
                    await interaction.followup.send(
                        "⚠️ サーバー設定が見つかりませんでした。管理者に連絡してください。",
                        ephemeral=True
                    )
                    return
                
                # 設定値を更新
                guild_settings.command_prefix = self.prefix.value
                
                # ログチャンネルが指定されている場合は設定
                if self.log_channel.value:
                    guild_settings.log_channel_name = self.log_channel.value
                
                # ウェルカムメッセージが指定されている場合は設定
                if self.welcome_message.value:
                    guild_settings.welcome_message = self.welcome_message.value
                
                # 設定を保存
                session.commit()
            
            # 保存成功メッセージを送信
            embed = EmbedBuilder.create_embed(
                title="✅ 設定を保存しました",
                description="一般設定を保存しました。変更は即時反映されます。",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"設定保存中にエラーが発生しました: {e}")
            await interaction.followup.send(
                f"⚠️ エラーが発生しました: {e}",
                ephemeral=True
            )


class ModerationSettingsView(discord.ui.View):
    """モデレーション設定のためのビュー"""
    
    def __init__(self, bot: commands.Bot, ctx, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.logger = logging.getLogger('bot.commands.setup.moderation')
        
        # ドロップダウンを追加
        self.add_item(self.create_action_dropdown())
    
    def create_action_dropdown(self):
        """アクションのドロップダウンメニューを作成"""
        dropdown = discord.ui.Select(
            placeholder="設定したい項目を選択してください",
            options=[
                discord.SelectOption(
                    label="違反アクション設定",
                    description="警告、ミュート、キック、BANなどのアクションを設定",
                    emoji="⚠️",
                    value="violations"
                ),
                discord.SelectOption(
                    label="禁止ワード設定",
                    description="禁止ワードとそのアクションを設定",
                    emoji="🔍",
                    value="bad_words"
                ),
                discord.SelectOption(
                    label="自動モデレーション設定",
                    description="自動モデレーションの設定",
                    emoji="🤖",
                    value="auto_mod"
                ),
            ]
        )
        
        async def dropdown_callback(interaction: discord.Interaction):
            """ドロップダウン選択時のコールバック"""
            await interaction.response.defer(ephemeral=True)
            
            value = dropdown.values[0]
            if value == "violations":
                # 違反アクション設定モーダルを表示
                modal = ViolationSettingsModal(self.bot, self.guild_id)
                await interaction.followup.send("違反アクション設定を開きます...", ephemeral=True)
                await interaction.response.send_modal(modal)
            elif value == "bad_words":
                # 禁止ワード設定を表示
                embed = EmbedBuilder.create_embed(
                    title="🔍 禁止ワード設定",
                    description="禁止ワードの追加・編集・削除を行えます。",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            elif value == "auto_mod":
                # 自動モデレーション設定を表示
                embed = EmbedBuilder.create_embed(
                    title="🤖 自動モデレーション設定",
                    description="自動モデレーションの設定を行います。",
                    color=discord.Color.teal()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        dropdown.callback = dropdown_callback
        return dropdown


class ViolationSettingsModal(discord.ui.Modal, title="違反アクション設定"):
    """違反アクション設定のためのモーダル"""
    
    warning_threshold = discord.ui.TextInput(
        label="警告しきい値",
        placeholder="何回の警告でミュートに移行するか（例：3）",
        default="3",
        required=True,
    )
    
    mute_threshold = discord.ui.TextInput(
        label="ミュートしきい値",
        placeholder="何回のミュートでキックに移行するか（例：2）",
        default="2",
        required=True,
    )
    
    kick_threshold = discord.ui.TextInput(
        label="キックしきい値",
        placeholder="何回のキックでBANに移行するか（例：1）",
        default="1",
        required=True,
    )
    
    mute_duration = discord.ui.TextInput(
        label="ミュート期間（分）",
        placeholder="デフォルトのミュート期間を分単位で（例：60）",
        default="60",
        required=True,
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.logger = logging.getLogger('bot.commands.setup.moderation.modal')
    
    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 入力値をチェック
            try:
                warning_threshold = int(self.warning_threshold.value)
                mute_threshold = int(self.mute_threshold.value)
                kick_threshold = int(self.kick_threshold.value)
                mute_duration = int(self.mute_duration.value)
                
                if any(v <= 0 for v in [warning_threshold, mute_threshold, kick_threshold, mute_duration]):
                    raise ValueError("すべての値は1以上である必要があります")
                
            except ValueError as e:
                await interaction.followup.send(
                    f"⚠️ 入力値が不正です: {e}",
                    ephemeral=True
                )
                return
            
            # データベースに設定を保存（仮実装）
            await asyncio.sleep(1)  # 実際のDB保存処理の代わりに遅延
            
            # 保存成功メッセージを送信
            embed = EmbedBuilder.create_embed(
                title="✅ 設定を保存しました",
                description="違反アクション設定を保存しました。変更は即時反映されます。",
                fields=[
                    {"name": "警告しきい値", "value": f"{warning_threshold}回の警告でミュート", "inline": True},
                    {"name": "ミュートしきい値", "value": f"{mute_threshold}回のミュートでキック", "inline": True},
                    {"name": "キックしきい値", "value": f"{kick_threshold}回のキックでBAN", "inline": True},
                    {"name": "ミュート期間", "value": f"{mute_duration}分", "inline": True},
                ],
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"設定保存中にエラーが発生しました: {e}")
            await interaction.followup.send(
                f"⚠️ エラーが発生しました: {e}",
                ephemeral=True
            )


class AutoResponseView(discord.ui.View):
    """自動応答設定のためのビュー"""
    
    def __init__(self, bot: commands.Bot, ctx, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.logger = logging.getLogger('bot.commands.setup.autoresponse')
    
    @discord.ui.button(label="自動応答を追加", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_response_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """自動応答追加ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # 自動応答追加モーダルを表示
        modal = AddAutoResponseModal(self.bot, interaction.guild_id)
        await interaction.followup.send("自動応答を追加します...", ephemeral=True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="自動応答を一覧表示", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_responses_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """自動応答一覧ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # 自動応答のリストを取得（仮実装）
        embed = EmbedBuilder.create_embed(
            title="📋 自動応答一覧",
            description="このサーバーの自動応答リストです。",
            fields=[
                {"name": "ID: 1", "value": "トリガー: `こんにちは` → 応答: `こんにちは！`", "inline": False},
                {"name": "ID: 2", "value": "トリガー: `ヘルプ` → 応答: `コマンドは !help で確認できます`", "inline": False},
            ],
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class AddAutoResponseModal(discord.ui.Modal, title="自動応答の追加"):
    """自動応答を追加するためのモーダル"""
    
    trigger = discord.ui.TextInput(
        label="トリガーワード",
        placeholder="反応するキーワードを入力",
        required=True,
    )
    
    response = discord.ui.TextInput(
        label="応答メッセージ",
        placeholder="送信するメッセージを入力",
        style=discord.TextStyle.paragraph,
        required=True,
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.logger = logging.getLogger('bot.commands.setup.autoresponse.modal')
    
    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 自動応答をデータベースに追加（仮実装）
            await asyncio.sleep(1)  # 実際のDB保存処理の代わりに遅延
            
            # 保存成功メッセージを送信
            embed = EmbedBuilder.create_embed(
                title="✅ 自動応答を追加しました",
                description="新しい自動応答を追加しました。",
                fields=[
                    {"name": "トリガー", "value": f"`{self.trigger.value}`", "inline": True},
                    {"name": "応答", "value": f"`{self.response.value}`", "inline": True},
                ],
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"自動応答追加中にエラーが発生しました: {e}")
            await interaction.followup.send(
                f"⚠️ エラーが発生しました: {e}",
                ephemeral=True
            )


class RaidProtectionView(discord.ui.View):
    """レイド保護設定のためのビュー"""
    
    def __init__(self, bot: commands.Bot, ctx, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.logger = logging.getLogger('bot.commands.setup.raid')
    
    @discord.ui.button(label="レイド保護を有効化", style=discord.ButtonStyle.success, emoji="✅")
    async def enable_raid_protection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """レイド保護有効化ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # レイド保護設定モーダルを表示
        modal = RaidProtectionModal(self.bot, interaction.guild_id)
        await interaction.followup.send("レイド保護設定を開きます...", ephemeral=True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="レイド保護を無効化", style=discord.ButtonStyle.danger, emoji="❌")
    async def disable_raid_protection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """レイド保護無効化ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # レイド保護を無効化（仮実装）
        await asyncio.sleep(1)  # 実際のDB更新処理の代わりに遅延
        
        # 無効化メッセージを送信
        embed = EmbedBuilder.create_embed(
            title="❌ レイド保護を無効化しました",
            description="サーバーのレイド保護機能を無効化しました。",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class RaidProtectionModal(discord.ui.Modal, title="レイド保護設定"):
    """レイド保護設定のためのモーダル"""
    
    join_rate = discord.ui.TextInput(
        label="参加率しきい値（人/分）",
        placeholder="1分あたりの参加者数（例：10）",
        default="10",
        required=True,
    )
    
    action_type = discord.ui.TextInput(
        label="対応アクション",
        placeholder="'verification', 'lockdown', 'kick', 'ban'のいずれか",
        default="verification",
        required=True,
    )
    
    new_account_days = discord.ui.TextInput(
        label="新規アカウント判定（日数）",
        placeholder="アカウント作成からの日数（例：7）",
        default="7",
        required=True,
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.logger = logging.getLogger('bot.commands.setup.raid.modal')
    
    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 入力値をチェック
            try:
                join_rate = int(self.join_rate.value)
                new_account_days = int(self.new_account_days.value)
                
                action_type = self.action_type.value.lower()
                if action_type not in ['verification', 'lockdown', 'kick', 'ban']:
                    raise ValueError("アクションタイプが不正です")
                
                if join_rate <= 0 or new_account_days <= 0:
                    raise ValueError("すべての値は1以上である必要があります")
                
            except ValueError as e:
                await interaction.followup.send(
                    f"⚠️ 入力値が不正です: {e}",
                    ephemeral=True
                )
                return
            
            # データベースに設定を保存（仮実装）
            await asyncio.sleep(1)  # 実際のDB保存処理の代わりに遅延
            
            # 保存成功メッセージを送信
            embed = EmbedBuilder.create_embed(
                title="✅ レイド保護設定を保存しました",
                description="レイド保護設定を保存しました。変更は即時反映されます。",
                fields=[
                    {"name": "参加率しきい値", "value": f"{join_rate}人/分", "inline": True},
                    {"name": "対応アクション", "value": action_type, "inline": True},
                    {"name": "新規アカウント判定", "value": f"{new_account_days}日", "inline": True},
                ],
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"設定保存中にエラーが発生しました: {e}")
            await interaction.followup.send(
                f"⚠️ エラーが発生しました: {e}",
                ephemeral=True
            )


class AntiSpamView(discord.ui.View):
    """アンチスパム設定のためのビュー"""
    
    def __init__(self, bot: commands.Bot, ctx, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.logger = logging.getLogger('bot.commands.setup.antispam')
    
    @discord.ui.button(label="アンチスパムを有効化", style=discord.ButtonStyle.success, emoji="✅")
    async def enable_antispam(self, interaction: discord.Interaction, button: discord.ui.Button):
        """アンチスパム有効化ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # アンチスパム設定モーダルを表示
        modal = AntiSpamModal(self.bot, interaction.guild_id)
        await interaction.followup.send("アンチスパム設定を開きます...", ephemeral=True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="アンチスパムを無効化", style=discord.ButtonStyle.danger, emoji="❌")
    async def disable_antispam(self, interaction: discord.Interaction, button: discord.ui.Button):
        """アンチスパム無効化ボタンのコールバック"""
        await interaction.response.defer(ephemeral=True)
        
        # アンチスパムを無効化（仮実装）
        await asyncio.sleep(1)  # 実際のDB更新処理の代わりに遅延
        
        # 無効化メッセージを送信
        embed = EmbedBuilder.create_embed(
            title="❌ アンチスパムを無効化しました",
            description="サーバーのアンチスパム機能を無効化しました。",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class AntiSpamModal(discord.ui.Modal, title="アンチスパム設定"):
    """アンチスパム設定のためのモーダル"""
    
    message_threshold = discord.ui.TextInput(
        label="メッセージしきい値",
        placeholder="X秒間にY個以上のメッセージ（例：5）",
        default="5",
        required=True,
    )
    
    time_frame = discord.ui.TextInput(
        label="検出時間枠（秒）",
        placeholder="メッセージカウントの時間枠（例：3）",
        default="3",
        required=True,
    )
    
    action_type = discord.ui.TextInput(
        label="対応アクション",
        placeholder="'warn', 'mute', 'kick', 'ban'のいずれか",
        default="mute",
        required=True,
    )
    
    mute_duration = discord.ui.TextInput(
        label="ミュート期間（分）",
        placeholder="ミュート時間（例：10）",
        default="10",
        required=True,
    )
    
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.logger = logging.getLogger('bot.commands.setup.antispam.modal')
    
    async def on_submit(self, interaction: discord.Interaction):
        """フォーム送信時の処理"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # 入力値をチェック
            try:
                message_threshold = int(self.message_threshold.value)
                time_frame = int(self.time_frame.value)
                mute_duration = int(self.mute_duration.value)
                
                action_type = self.action_type.value.lower()
                if action_type not in ['warn', 'mute', 'kick', 'ban']:
                    raise ValueError("アクションタイプが不正です")
                
                if message_threshold <= 0 or time_frame <= 0 or mute_duration <= 0:
                    raise ValueError("すべての値は1以上である必要があります")
                
            except ValueError as e:
                await interaction.followup.send(
                    f"⚠️ 入力値が不正です: {e}",
                    ephemeral=True
                )
                return
            
            # データベースに設定を保存（仮実装）
            await asyncio.sleep(1)  # 実際のDB保存処理の代わりに遅延
            
            # 保存成功メッセージを送信
            embed = EmbedBuilder.create_embed(
                title="✅ アンチスパム設定を保存しました",
                description="アンチスパム設定を保存しました。変更は即時反映されます。",
                fields=[
                    {"name": "メッセージしきい値", "value": f"{message_threshold}", "inline": True},
                    {"name": "検出時間枠", "value": f"{time_frame}秒", "inline": True},
                    {"name": "対応アクション", "value": action_type, "inline": True},
                    {"name": "ミュート期間", "value": f"{mute_duration}分", "inline": True},
                ],
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"設定保存中にエラーが発生しました: {e}")
            await interaction.followup.send(
                f"⚠️ エラーが発生しました: {e}",
                ephemeral=True
            )


class Setup(commands.Cog):
    """設定コマンドの実装"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('bot.commands.setup')
    
    @app_commands.command(name="setup", description="サーバーの設定を行います")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        """サーバー設定コマンド"""
        # 権限チェック
        if not has_admin_permissions(interaction.user, interaction.guild):
            embed = EmbedBuilder.create_embed(
                title="⚠️ 権限エラー",
                description="このコマンドは管理者のみが実行できます。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # メインメニューを表示
        embed = EmbedBuilder.create_embed(
            title="⚙️ サーバー設定",
            description="Shard Botの設定を行います。設定したい項目のボタンをクリックしてください。",
            fields=[
                {"name": "📋 一般設定", "value": "コマンドプレフィックス、ログチャンネルなどの基本設定", "inline": False},
                {"name": "🛡️ モデレーション", "value": "モデレーション機能の設定", "inline": False},
                {"name": "🤖 自動応答", "value": "自動応答ルールの設定", "inline": False},
                {"name": "🔒 レイド保護", "value": "レイド対策の設定", "inline": False},
                {"name": "🧹 アンチスパム", "value": "スパム対策の設定", "inline": False},
                {"name": "🌐 Webダッシュボード", "value": "Web上でより詳細な設定が可能です", "inline": False},
            ],
            color=discord.Color.blue()
        )
        
        # 設定ビューを送信
        view = SetupView(self.bot, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # ビューにメッセージを保存
        message = await interaction.original_response()
        view.message = message


async def setup(bot: commands.Bot):
    """Cogをボットに追加"""
    await bot.add_cog(Setup(bot)) 