from discord.ext import commands
from discord import app_commands
import discord
import logging
import os
from typing import Optional, Dict, Any
import yaml

logger = logging.getLogger('commands.admin.setup')

class AuthView(discord.ui.View):
    """認証用の電卓風UIを提供するビュー"""
    def __init__(self, author_id: int, target_code: str, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.target_code = target_code
        self.input_value = ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("この認証はあなた専用です。", ephemeral=True)
            return False
        return True

    async def update_message(self, interaction: discord.Interaction):
        content = f"入力内容: `{self.input_value}`"
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def btn_1(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "1"
        await self.update_message(interaction)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def btn_2(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "2"
        await self.update_message(interaction)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def btn_3(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "3"
        await self.update_message(interaction)

    @discord.ui.button(label="4", style=discord.ButtonStyle.primary, row=1)
    async def btn_4(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "4"
        await self.update_message(interaction)

    @discord.ui.button(label="5", style=discord.ButtonStyle.primary, row=1)
    async def btn_5(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "5"
        await self.update_message(interaction)

    @discord.ui.button(label="6", style=discord.ButtonStyle.primary, row=1)
    async def btn_6(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "6"
        await self.update_message(interaction)

    @discord.ui.button(label="7", style=discord.ButtonStyle.primary, row=2)
    async def btn_7(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "7"
        await self.update_message(interaction)

    @discord.ui.button(label="8", style=discord.ButtonStyle.primary, row=2)
    async def btn_8(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "8"
        await self.update_message(interaction)

    @discord.ui.button(label="9", style=discord.ButtonStyle.primary, row=2)
    async def btn_9(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "9"
        await self.update_message(interaction)

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.secondary, row=3)
    async def btn_clear(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value = ""
        await self.update_message(interaction)

    @discord.ui.button(label="0", style=discord.ButtonStyle.primary, row=3)
    async def btn_0(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.input_value += "0"
        await self.update_message(interaction)

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.success, row=3)
    async def btn_submit(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.input_value == self.target_code:
            role = discord.utils.get(interaction.guild.roles, name="✅ >> Verified User")
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.response.edit_message(content="認証に成功しました！", view=None)
                except Exception as e:
                    await interaction.response.send_message("ロールの付与に失敗しました。", ephemeral=True)
            else:
                await interaction.response.send_message("認証ロールが存在しません。", ephemeral=True)
            self.stop()
        else:
            self.input_value = ""
            await interaction.response.edit_message(content="認証に失敗しました。もう一度入力してください。\n入力内容: ``", view=self)

class AuthPanel(discord.ui.View):
    """認証パネル用のビュー"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="認証開始", style=discord.ButtonStyle.success)
    async def start_auth(self, button: discord.ui.Button, interaction: discord.Interaction):
        code, image_bytes = self.bot.generate_captcha()
        file = discord.File(fp=image_bytes, filename="captcha.png")
        embed = discord.Embed(
            title="🔒 認証",
            description="以下の画像に表示されている数字を入力してください。\n入力内容: ``",
            color=0x00ff00
        )
        embed.set_image(url="attachment://captcha.png")
        view = AuthView(author_id=interaction.user.id, target_code=code)
        try:
            await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.setup_in_progress = {}  # サーバーごとのセットアップ状態を追跡

    @app_commands.command(name="setup", description="サーバーのセットアップを開始します")
    @app_commands.describe(
        password="セットアップ用のパスワードを入力してください",
        permissions="権限ロール作成を有効にします（デフォルトTrue）",
        category="カテゴリロール作成を有効にします（デフォルトTrue）",
        create_bot_role="BOTロール作成を有効にします（デフォルトTrue）"
    )
    @app_commands.guild_only()
    async def setup(
        self,
        interaction: discord.Interaction,
        password: str,
        permissions: bool = True,
        category: bool = True,
        create_bot_role: bool = True
    ):
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
            return

        # 既に実行中かチェック
        if interaction.guild_id in self.setup_in_progress:
            await interaction.response.send_message("セットアップは既に実行中です。完了までお待ちください。", ephemeral=True)
            return

        # パスワード確認
        if password != os.getenv('SETUP_PASSWORD'):
            await interaction.response.send_message("パスワードが正しくありません。", ephemeral=True)
            return

        try:
            # セットアップ開始を記録
            self.setup_in_progress[interaction.guild_id] = True
            
            # 開始メッセージを送信
            await interaction.response.defer()
            start_embed = discord.Embed(
                title="🚀 セットアップ開始",
                description="サーバーのセットアップを開始します...",
                color=0x00ff00
            )
            await interaction.followup.send(embed=start_embed)
            
            # ロールセットアップ開始
            total_steps = 1 + (10 if permissions else 0) + 1 + (4 if category else 0) + (1 if create_bot_role else 0)
            current_step = 0
            logs = []

            # プログレスメッセージ
            progress_embed = discord.Embed(
                title="ロールセットアップ進行状況",
                description=self.bot.build_progress_bar(current_step, total_steps),
                color=0x00ff00
            )
            progress_message = await interaction.followup.send(embed=progress_embed)

            # 既存のロール削除
            for role in interaction.guild.roles:
                if role.is_default():
                    continue
                try:
                    await role.delete(reason="Setup command: Existing role deletion")
                except Exception as e:
                    logs.append(f"【削除失敗】ロール '{role.name}' の削除に失敗しました。")
            current_step += 1
            logs.append("既存のロールを削除しました。")
            
            # 進捗更新
            progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
            try:
                await progress_message.edit(embed=progress_embed)
            except discord.NotFound:
                progress_message = await interaction.followup.send(embed=progress_embed)

            # 権限ロールの作成
            if permissions:
                permission_roles = [
                    ("管理者", discord.Permissions(administrator=True)),
                    ("サーバー管理", discord.Permissions(manage_guild=True)),
                    ("BAN権限", discord.Permissions(ban_members=True)),
                    ("メンバー管理権限", discord.Permissions(kick_members=True, mute_members=True)),
                    ("VC管理権限", discord.Permissions(move_members=True, mute_members=True, deafen_members=True)),
                    ("ロール管理", discord.Permissions(manage_roles=True)),
                    ("チャンネル管理", discord.Permissions(manage_channels=True)),
                    ("メッセージ管理", discord.Permissions(manage_messages=True)),
                    ("everyoneメンション権限", discord.Permissions(mention_everyone=True)),
                    ("絵文字・イベント管理", discord.Permissions(manage_emojis=True, manage_events=True))
                ]
                for role_name, perms in permission_roles:
                    try:
                        await interaction.guild.create_role(
                            name=role_name,
                            permissions=perms,
                            color=discord.Colour.default(),
                            reason="Setup command: Permission role creation"
                        )
                        logs.append(f"ロール '{role_name}' を作成しました。")
                    except Exception as e:
                        logs.append(f"【作成失敗】ロール '{role_name}' の作成に失敗しました。")
                    current_step += 1
                    progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                    try:
                        await progress_message.edit(embed=progress_embed)
                    except discord.NotFound:
                        progress_message = await interaction.followup.send(embed=progress_embed)

            # everyoneロールの権限更新
            try:
                everyone_role = interaction.guild.default_role
                new_perms = discord.Permissions(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
                await everyone_role.edit(
                    permissions=new_perms,
                    reason="Setup command: everyone role update"
                )
                logs.append("everyoneロールの権限を更新しました。")
            except Exception as e:
                logs.append("【更新失敗】everyoneロールの権限更新に失敗しました。")
            current_step += 1
            progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
            try:
                await progress_message.edit(embed=progress_embed)
            except discord.NotFound:
                progress_message = await interaction.followup.send(embed=progress_embed)

            # カテゴリロールの作成
            if category:
                category_roles = [
                    "-----役職ロール-----",
                    "-----権限ロール-----",
                    "-----BOTロール-----",
                    "-----各種システムロール-----"
                ]
                for cat_role in category_roles:
                    try:
                        await interaction.guild.create_role(
                            name=cat_role,
                            permissions=discord.Permissions.none(),
                            color=discord.Colour.default(),
                            reason="Setup command: Category role creation"
                        )
                        logs.append(f"カテゴリロール '{cat_role}' を作成しました。")
                    except Exception as e:
                        logs.append(f"【作成失敗】カテゴリロール '{cat_role}' の作成に失敗しました。")
                    current_step += 1
                    progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                    try:
                        await progress_message.edit(embed=progress_embed)
                    except discord.NotFound:
                        progress_message = await interaction.followup.send(embed=progress_embed)

            # BOTロールの作成
            if create_bot_role:
                try:
                    await interaction.guild.create_role(
                        name="BOT",
                        permissions=discord.Permissions.none(),
                        color=discord.Colour.default(),
                        reason="Setup command: BOT role creation"
                    )
                    logs.append("BOTロールを作成しました。")
                except Exception as e:
                    logs.append("【作成失敗】BOTロールの作成に失敗しました。")
                current_step += 1
                progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                try:
                    await progress_message.edit(embed=progress_embed)
                except discord.NotFound:
                    progress_message = await interaction.followup.send(embed=progress_embed)

            # 完了メッセージ
            complete_embed = discord.Embed(
                title="✅ セットアップ完了",
                description="\n".join(logs),
                color=0x00ff00
            )
            try:
                await interaction.followup.send(embed=complete_embed)
            except Exception as e:
                self.bot.logger.error(f"Failed to send completion message: {e}")

        except Exception as e:
            error_embed = discord.Embed(
                title="⚠️ エラー発生",
                description=f"セットアップ中にエラーが発生しました:\n```py\n{str(e)}\n```",
                color=0xff0000
            )
            try:
                await interaction.followup.send(embed=error_embed)
            except Exception:
                pass
            self.bot.logger.error(f"Setup error: {e}", exc_info=True)
            
        finally:
            # セットアップ完了を記録
            if interaction.guild_id in self.setup_in_progress:
                del self.setup_in_progress[interaction.guild_id]

    async def create_channels(
        self,
        guild: discord.Guild,
        categories_config: Dict[str, Any],
        skip_channel_id: Optional[int] = None
    ):
        """チャンネルを作成します"""
        # 既存のチャンネルとカテゴリを削除
        for channel in guild.channels:
            if skip_channel_id and channel.id == skip_channel_id:
                continue
            try:
                await channel.delete()
                logger.info(f"Deleted channel: {channel.name}")
            except Exception as e:
                logger.error(f"Error deleting channel {channel.name}: {e}")

        # カテゴリとチャンネルの作成
        for category_data in categories_config.values():
            try:
                category = await guild.create_category(
                    name=category_data['name'],
                    reason="Setup command: Category creation"
                )
                logger.info(f"Created category: {category_data['name']}")

                for channel_data in category_data['channels']:
                    for channel_info in channel_data.values():
                        channel_type = discord.ChannelType.voice if channel_info.get('type') == 'voice' else discord.ChannelType.text
                        
                        if channel_type == discord.ChannelType.text:
                            channel = await category.create_text_channel(
                                name=channel_info['name'],
                                topic=channel_info['description'],
                                reason="Setup command: Channel creation"
                            )
                        else:
                            channel = await category.create_voice_channel(
                                name=channel_info['name'],
                                reason="Setup command: Channel creation"
                            )
                        
                        logger.info(f"Created channel: {channel_info['name']}")
            except Exception as e:
                logger.error(f"Error in category {category_data['name']}: {e}")

    async def create_roles(self, guild: discord.Guild, roles_config: Dict[str, Any]):
        """ロールを作成します"""
        existing_roles = {role.name: role for role in guild.roles}
        
        for category in roles_config.values():
            for role_data in category.values():
                if role_data['name'] not in existing_roles:
                    try:
                        await guild.create_role(
                            name=role_data['name'],
                            permissions=discord.Permissions(),
                            colour=discord.Colour(int(role_data['color'].lstrip('#'), 16)),
                            reason="Setup command: Role creation"
                        )
                        logger.info(f"Created role: {role_data['name']}")
                    except Exception as e:
                        logger.error(f"Error creating role {role_data['name']}: {e}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Setup(bot)) 