from discord.ext import commands
from discord import app_commands
import discord
import logging
import os
import shutil
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
        create_bot_role="BOTロール作成を有効にします（デフォルトTrue）",
        roles_only="ロールのみをセットアップします（デフォルトFalse）",
        use_role_yml="roles.ymlファイルに定義されたロールを使用します（デフォルトTrue）"
    )
    @app_commands.guild_only()
    async def setup(
        self,
        interaction: discord.Interaction,
        password: str,
        permissions: bool = True,
        category: bool = True,
        create_bot_role: bool = True,
        roles_only: bool = False,
        use_role_yml: bool = True
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
                description=f"サーバーのセットアップを開始します...\n{'ロールのみ' if roles_only else '完全'}セットアップを実行します。",
                color=0x00ff00
            )
            await interaction.followup.send(embed=start_embed)
            
            # ロールセットアップ開始
            total_steps = 1  # 既存ロール削除
            if permissions:
                total_steps += 10  # 権限ロール
            total_steps += 1  # everyoneロール更新
            if use_role_yml:
                total_steps += 1  # roles.ymlからのロード
            if category and not roles_only:
                total_steps += 4  # カテゴリロール
            if create_bot_role and not roles_only:
                total_steps += 1  # BOTロール
            if not roles_only:
                total_steps += 1  # チャンネル作成
            
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
            
            # roles.ymlからロールを作成
            if use_role_yml:
                try:
                    # roles.ymlファイルのパスを取得
                    roles_file_path = os.path.join(os.getcwd(), "roles.yml")
                    if not os.path.exists(roles_file_path):
                        roles_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "roles.yml")
                    
                    if os.path.exists(roles_file_path):
                        with open(roles_file_path, 'r', encoding='utf-8') as file:
                            roles_config = yaml.safe_load(file)
                        
                        if roles_config and 'roles' in roles_config:
                            # すべてのカテゴリのロールを作成
                            for category_name, roles in roles_config['roles'].items():
                                for role_id, role_info in roles.items():
                                    try:
                                        # パーミッションの設定
                                        perms = discord.Permissions()
                                        if 'permissions' in role_info:
                                            if role_info['permissions'] == 'all':
                                                perms = discord.Permissions.all()
                                            else:
                                                for perm in role_info['permissions']:
                                                    setattr(perms, perm, True)
                                        
                                        # 色の設定
                                        color = discord.Colour.default()
                                        if 'color' in role_info:
                                            color_str = role_info['color']
                                            if color_str.startswith('#'):
                                                color = discord.Colour.from_rgb(
                                                    int(color_str[1:3], 16),
                                                    int(color_str[3:5], 16),
                                                    int(color_str[5:7], 16)
                                                )
                                        
                                        # ロール作成
                                        await interaction.guild.create_role(
                                            name=role_info['name'],
                                            permissions=perms,
                                            color=color,
                                            hoist=role_info.get('hoist', False),
                                            mentionable=role_info.get('mentionable', True),
                                            reason=f"Setup command: {category_name} role creation from roles.yml"
                                        )
                                        logs.append(f"ロール '{role_info['name']}' を作成しました。")
                                    except Exception as e:
                                        logs.append(f"【作成失敗】ロール '{role_info.get('name', role_id)}' の作成に失敗しました: {str(e)}")
                            
                            logs.append("roles.ymlからロールを作成しました。")
                        else:
                            logs.append("【警告】roles.ymlファイルに有効なロール設定が見つかりませんでした。")
                    else:
                        logs.append("【警告】roles.ymlファイルが見つかりませんでした。")
                except Exception as e:
                    logs.append(f"【エラー】roles.ymlからのロール作成中にエラーが発生しました: {str(e)}")
                
                current_step += 1
                progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                try:
                    await progress_message.edit(embed=progress_embed)
                except discord.NotFound:
                    progress_message = await interaction.followup.send(embed=progress_embed)

            # ロールのみのセットアップならここで終了
            if roles_only:
                # 完了メッセージ
                complete_embed = discord.Embed(
                    title="✅ セットアップ完了",
                    description="ロールのセットアップが完了しました。",
                    color=0x00ff00
                )
                log_text = "\n".join(logs)
                if len(log_text) > 1000:
                    log_text = log_text[:997] + "..."
                complete_embed.add_field(name="セットアップログ", value=log_text)
                await interaction.followup.send(embed=complete_embed)
                
                # セットアップ状態をクリア
                self.setup_in_progress.pop(interaction.guild_id, None)
                return

            # カテゴリロールの作成
            if category and not roles_only:
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
            if create_bot_role and not roles_only:
                try:
                    bot_role = await interaction.guild.create_role(
                        name="BOT",
                        permissions=discord.Permissions(view_channel=True),
                        color=discord.Colour.from_rgb(255, 0, 0),  # 赤色
                        hoist=True,
                        mentionable=False,
                        reason="Setup command: BOT role creation"
                    )
                    logs.append("BOTロールを作成しました。")
                    
                    # BOTにロールを付与
                    for member in interaction.guild.members:
                        if member.bot:
                            try:
                                await member.add_roles(bot_role, reason="Setup command: Assigning BOT role")
                            except Exception as e:
                                logs.append(f"【付与失敗】BOT '{member.display_name}' へのロール付与に失敗しました。")
                except Exception as e:
                    logs.append("【作成失敗】BOTロールの作成に失敗しました。")
                
                current_step += 1
                progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                try:
                    await progress_message.edit(embed=progress_embed)
                except discord.NotFound:
                    progress_message = await interaction.followup.send(embed=progress_embed)

            # チャンネルの作成
            if not roles_only:
                try:
                    # categories.ymlファイルの読み込み
                    categories_yml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..', 'categories.yml')
                    if os.path.exists(categories_yml_path):
                        with open(categories_yml_path, 'r', encoding='utf-8') as f:
                            categories_config = yaml.safe_load(f)
                        
                        progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                        progress_embed.title = "チャンネルセットアップ進行状況"
                        try:
                            await progress_message.edit(embed=progress_embed)
                        except discord.NotFound:
                            progress_message = await interaction.followup.send(embed=progress_embed)
                        
                        # チャンネルの作成（コマンドチャンネルは削除しない）
                        skip_channel_id = interaction.channel.id
                        channel_logs = await self.create_channels(interaction.guild, categories_config.get('categories', {}), skip_channel_id)
                        logs.extend(channel_logs)
                        
                        current_step += 1
                        progress_embed.description = self.bot.build_progress_bar(current_step, total_steps)
                        try:
                            await progress_message.edit(embed=progress_embed)
                        except discord.NotFound:
                            progress_message = await interaction.followup.send(embed=progress_embed)
                    else:
                        logs.append("【警告】categories.ymlファイルが見つからなかったため、チャンネル作成をスキップしました。")
                except Exception as e:
                    logs.append(f"【エラー】チャンネル作成中にエラーが発生しました: {str(e)}")
                    logger.error(f"Error creating channels: {e}", exc_info=True)

            # 完了メッセージ
            complete_embed = discord.Embed(
                title="✅ セットアップ完了",
                description=f"{'ロールのみの' if roles_only else 'サーバーの'}セットアップが完了しました。",
                color=0x00ff00
            )
            log_text = "\n".join(logs)
            if len(log_text) > 1000:
                log_text = log_text[:997] + "..."
            complete_embed.add_field(name="セットアップログ", value=log_text)
            await interaction.followup.send(embed=complete_embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ セットアップエラー",
                description=f"セットアップ中にエラーが発生しました: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)
            logging.error(f"Setup error in guild {interaction.guild_id}: {str(e)}")
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
        """チャンネルを作成します。作成ログのリストを返します。"""
        logs = []  # 作成ログを記録するリスト
        
        # 既存のチャンネルとカテゴリを削除
        for channel in guild.channels:
            if skip_channel_id and channel.id == skip_channel_id:
                continue
            try:
                await channel.delete()
                logs.append(f"チャンネル '{channel.name}' を削除しました。")
                logger.info(f"Deleted channel: {channel.name}")
            except Exception as e:
                logs.append(f"【削除失敗】チャンネル '{channel.name}' の削除に失敗しました。")
                logger.error(f"Error deleting channel {channel.name}: {e}")

        # カテゴリとチャンネルの作成
        for category_name, category_data in categories_config.items():
            try:
                category = await guild.create_category(
                    name=category_data['name'],
                    reason="Setup command: Category creation"
                )
                logs.append(f"カテゴリ '{category_data['name']}' を作成しました。")
                logger.info(f"Created category: {category_data['name']}")

                for channel_data in category_data['channels']:
                    for channel_name, channel_info in channel_data.items():
                        channel_type = discord.ChannelType.voice if channel_info.get('type') == 'voice' else discord.ChannelType.text
                        
                        if channel_type == discord.ChannelType.text:
                            channel = await category.create_text_channel(
                                name=channel_info['name'],
                                topic=channel_info.get('description', ''),
                                reason="Setup command: Channel creation"
                            )
                        else:
                            channel = await category.create_voice_channel(
                                name=channel_info['name'],
                                reason="Setup command: Channel creation"
                            )
                        
                        logs.append(f"チャンネル '{channel_info['name']}' を作成しました。")
                        logger.info(f"Created channel: {channel_info['name']}")
                        
                        # チャンネルの権限設定（permissions が定義されている場合）
                        if 'permissions' in channel_info:
                            for permission_setting in channel_info['permissions']:
                                for permission_name, role_name in permission_setting.items():
                                    role = discord.utils.get(guild.roles, name=role_name)
                                    if role:
                                        if permission_name == 'view_channel':
                                            await channel.set_permissions(role, view_channel=True)
                                        elif permission_name == 'send_messages':
                                            await channel.set_permissions(role, send_messages=True)
                                        elif permission_name == 'connect':
                                            await channel.set_permissions(role, connect=True)
                                        elif permission_name == 'speak':
                                            await channel.set_permissions(role, speak=True)
                                    elif role_name == 'everyone':
                                        # everyoneロールの場合
                                        await channel.set_permissions(guild.default_role, 
                                                                    view_channel=permission_name=='view_channel',
                                                                    send_messages=permission_name=='send_messages')
            except Exception as e:
                logs.append(f"【エラー】カテゴリ '{category_name}' の処理中にエラーが発生しました: {str(e)}")
                logger.error(f"Error in category {category_name}: {e}")
                
        return logs  # 作成ログを返す

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
    
    # roles.ymlファイルの作成
    try:
        # ソースファイルのパス
        roles_yml_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..', 'roles.yml')
        # 宛先フォルダ（botディレクトリ内）
        roles_yml_destination = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..', 'roles.yml')
        
        # roles.ymlがすでに存在するか確認
        if not os.path.exists(roles_yml_destination):
            # コピー実行
            shutil.copy2(roles_yml_source, roles_yml_destination)
            logger.info(f"roles.yml をコピーしました: {roles_yml_destination}")
    except Exception as e:
        logger.error(f"roles.yml のコピーに失敗しました: {e}", exc_info=True)
        
    # categories.ymlファイルの作成
    try:
        # ソースファイルのパス
        categories_yml_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..', 'categories.yml')
        # 宛先フォルダ（botディレクトリ内）
        categories_yml_destination = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..', 'categories.yml')
        
        # categories.ymlがすでに存在するか確認
        if not os.path.exists(categories_yml_destination):
            # コピー実行
            shutil.copy2(categories_yml_source, categories_yml_destination)
            logger.info(f"categories.yml をコピーしました: {categories_yml_destination}")
    except Exception as e:
        logger.error(f"categories.yml のコピーに失敗しました: {e}", exc_info=True) 