import discord
from discord import app_commands
import yaml
import json
from typing import Dict, Any, Tuple
import logging
import os
from dotenv import load_dotenv
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont
import discord.ui

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Botの設定
class SetupBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = SetupBot()

# 環境変数の読み込み
load_dotenv()

# 環境変数からパスワードとトークンを取得
SETUP_PASSWORD = os.getenv('SETUP_PASSWORD')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 環境変数のバリデーション
def validate_env_vars():
    required_vars = ['BOT_TOKEN', 'SETUP_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set them in your .env file"
        )

# 起動時に環境変数をチェック
validate_env_vars()

# 設定ファイルの読み込み
def load_config(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# ロールの作成
async def create_roles(guild: discord.Guild, roles_config: Dict[str, Any]):
    existing_roles = {role.name: role for role in guild.roles}
    
    for category in roles_config.values():
        for role_data in category.values():
            if role_data['name'] not in existing_roles:
                try:
                    await guild.create_role(
                        name=role_data['name'],
                        permissions=discord.Permissions(),
                        colour=discord.Colour(int(role_data['color'].lstrip('#'), 16)),
                        reason="Automated role creation"
                    )
                    logger.info(f"Created role: {role_data['name']}")
                except Exception as e:
                    logger.error(f"Error creating role {role_data['name']}: {e}")

# チャンネルの作成
async def create_channels(guild: discord.Guild, categories_config: Dict[str, Any], skip_channel_id: int = None):
    # 既存のチャンネルとカテゴリを削除（※コマンド実行チャンネルは削除対象から除外）
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
                reason="Automated category creation"
            )
            logger.info(f"Created category: {category_data['name']}")

            for channel_data in category_data['channels']:
                for channel_info in channel_data.values():
                    channel_type = discord.ChannelType.voice if channel_info.get('type') == 'voice' else discord.ChannelType.text
                    
                    channel = await category.create_text_channel(
                        name=channel_info['name'],
                        topic=channel_info['description'],
                        reason="Automated channel creation"
                    ) if channel_type == discord.ChannelType.text else await category.create_voice_channel(
                        name=channel_info['name'],
                        reason="Automated channel creation"
                    )
                    
                    logger.info(f"Created channel: {channel_info['name']}")
        except Exception as e:
            logger.error(f"Error in category {category_data['name']}: {e}")

# 埋め込みメッセージの作成用ヘルパー関数
def create_embed(title: str, description: str, color: int = 0x00ff00) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Server Setup Bot", icon_url=client.user.avatar.url if client.user.avatar else None)
    return embed

@client.event
async def on_ready():
    logger.info(f'Bot is ready: {client.user.name}')

@client.tree.command(name="start", description="サーバーのセットアップを開始します")
@app_commands.describe(
    password="セットアップ用のパスワードを入力してください",
    permissions="権限ロール作成を有効にします（デフォルトTrue）",
    category="カテゴリロール作成を有効にします（デフォルトTrue）",
    create_bot_role="BOTロール作成を有効にします（デフォルトTrue）"
)
async def start(interaction: discord.Interaction, password: str, permissions: bool = True, category: bool = True, create_bot_role: bool = True):
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    # パスワード確認
    if password != SETUP_PASSWORD:
        error_embed = create_embed(
            "⚠️ エラー",
            "パスワードが正しくありません。",
            0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    try:
        # 開始メッセージ
        await interaction.response.defer()
        
        start_embed = create_embed(
            "🚀 セットアップ開始",
            "サーバーのセットアップを開始します..."
        )
        await interaction.followup.send(embed=start_embed)

        # 【ロールセットアップ開始】

        total_steps = 1 + (10 if permissions else 0) + 1 + (4 if category else 0) + (1 if create_bot_role else 0)
        current_step = 0
        logs = []

        def update_progress():
            progress = build_progress_bar(current_step, total_steps)
            embed = discord.Embed(title="ロールセットアップ進行状況", description=progress, color=0x00ff00)
            return embed

        progress_message = await interaction.followup.send(embed=update_progress())
        guild = interaction.guild

        # Step 1: 既存のロール削除（@everyone以外）
        for role in guild.roles:
            if role.is_default():
                continue
            try:
                await role.delete(reason="Start command: Existing role deletion")
            except Exception as e:
                logs.append(f"【削除失敗】ロール '{role.name}' の削除に失敗しました。")
        current_step += 1
        logs.append("既存のロールを削除しました。")
        await progress_message.edit(embed=update_progress())

        # Step 2: 権限ロールの作成（permissionsがTrueの場合）
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
                    await guild.create_role(
                        name=role_name,
                        permissions=perms,
                        color=discord.Colour.default(),
                        reason="Start command: Permission role creation"
                    )
                    logs.append(f"ロール '{role_name}' を作成しました。")
                except Exception as e:
                    logs.append(f"【作成失敗】ロール '{role_name}' の作成に失敗しました。")
                current_step += 1
                await progress_message.edit(embed=update_progress())

        # Step 3: everyoneロールの権限更新
        try:
            everyone_role = guild.default_role
            new_perms = discord.Permissions(view_channel=True, send_messages=True, read_message_history=True)
            await everyone_role.edit(permissions=new_perms, reason="Start command: everyone role update")
            logs.append("everyoneロールの権限を更新しました。")
        except Exception as e:
            logs.append("【更新失敗】everyoneロールの権限更新に失敗しました。")
        current_step += 1
        await progress_message.edit(embed=update_progress())

        # Step 4: カテゴリロールの作成（categoryがTrueの場合）
        if category:
            category_roles = [
                "-----役職ロール-----",
                "-----権限ロール-----",
                "-----BOTロール-----",
                "-----各種システムロール-----"
            ]
            for cat_role in category_roles:
                try:
                    await guild.create_role(
                        name=cat_role,
                        permissions=discord.Permissions.none(),
                        color=discord.Colour.default(),
                        reason="Start command: Category role creation"
                    )
                    logs.append(f"カテゴリロール '{cat_role}' を作成しました。")
                except Exception as e:
                    logs.append(f"【作成失敗】カテゴリロール '{cat_role}' の作成に失敗しました。")
                current_step += 1
                await progress_message.edit(embed=update_progress())

        # Step 5: BOTロールの作成（create_bot_roleがTrueの場合）
        if create_bot_role:
            try:
                await guild.create_role(
                    name="BOT",
                    permissions=discord.Permissions.none(),
                    color=discord.Colour.default(),
                    reason="Start command: BOT role creation"
                )
                logs.append("ロール 'BOT' を作成しました。")
            except Exception as e:
                logs.append("【作成失敗】ロール 'BOT' の作成に失敗しました。")
            current_step += 1
            await progress_message.edit(embed=update_progress())

        # ロールセットアップ完了ログ表示
        final_role_embed = discord.Embed(title="ロールセットアップ完了", color=0x00ff00)
        final_role_embed.add_field(name="ロール作成ログ", value="\n".join(logs), inline=False)
        final_role_embed.set_footer(text="ロール設定が完了しました。")
        await progress_message.edit(embed=final_role_embed)

        # チャンネル作成開始
        channels_embed = create_embed(
            "⚙️ チャンネル作成中",
            "チャンネルを作成しています..."
        )
        await interaction.followup.send(embed=channels_embed)
        categories_config = load_config('categories.yml')
        await create_channels(interaction.guild, categories_config['categories'], skip_channel_id=interaction.channel.id)

        # セットアップ完了メッセージ（ロール＆チャンネル作成完了）
        complete_embed = create_embed(
            "🎉 セットアップ完了",
            "✅ ロールセットアップ\n✅ チャンネル作成"
        )
        await interaction.followup.send(embed=complete_embed)

        # role.yml に書かれたロールも作成
        roles_config = load_config('roles.yml')
        await create_roles(interaction.guild, roles_config['roles'])
        # ログに追記
        final_logs = "role.ymlに書いてあるロールも作成しました。"

        # 終了メッセージ送信（全セットアップ完了）
        final_embed = create_embed(
            "✅ 全セットアップ完了",
            final_logs
        )
        await interaction.followup.send(embed=final_embed)

        # 最後に認証パネルを設置
        auth_panel_embed = create_embed(
            "🔒 認証パネル",
            "下の【認証開始】ボタンを押して認証を行ってください。"
        )
        await interaction.followup.send(embed=auth_panel_embed, view=AuthPanel())

    except Exception as e:
        error_embed = create_embed(
            "⚠️ エラー発生",
            f"セットアップ中にエラーが発生しました:\n{str(e)}",
            0xff0000
        )
        await interaction.followup.send(embed=error_embed)
        logger.error(f"Setup error: {e}")

def generate_captcha(length: int = 4) -> Tuple[str, io.BytesIO]:
    """
    ランダムな数字を生成し、キャプチャ画像を作成してBytesIOオブジェクトとして返します。
    """
    code = ''.join(random.choices(string.digits, k=length))
    # 背景サイズなどの設定
    width, height = 120, 60
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    # フォント設定（arial.ttf が無い場合はデフォルトフォント）
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
    # テキストを中央に配置
    text_width, text_height = draw.textsize(code, font=font)
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    draw.text((x, y), code, font=font, fill=(0, 0, 0))
    # ノイズ（線）を追加
    for _ in range(10):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(0, 0, 0), width=1)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return code, image_bytes

class AuthView(discord.ui.View):
    """
    電卓風のボタン群を提供する View です。ユーザーが入力した数字を比較し、
    一致すれば認証ロールを付与します。
    """
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
        # 現在の入力状態を更新
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
            # 認証成功：認証ロールを付与
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
            # 認証失敗：入力をリセット
            self.input_value = ""
            await interaction.response.edit_message(content="認証に失敗しました。もう一度入力してください。\n入力内容: ``", view=self)

# 新規追加: 認証パネル用の View
class AuthPanel(discord.ui.View):
    @discord.ui.button(label="認証開始", style=discord.ButtonStyle.success)
    async def start_auth(self, button: discord.ui.Button, interaction: discord.Interaction):
        # ボタン押下時、キャプチャ画像と入力UI（AuthView）をエフェメラルメッセージで送信
        code, image_bytes = generate_captcha()
        file = discord.File(fp=image_bytes, filename="captcha.png")
        description = "以下の画像に表示されている数字を入力してください。\n入力内容: ``"
        embed = create_embed("🔒 認証", description)
        embed.set_image(url="attachment://captcha.png")
        view = AuthView(author_id=interaction.user.id, target_code=code)
        try:
            await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)

def build_progress_bar(current: int, total: int, bar_length: int = 20) -> str:
    filled = int((bar_length * current) // total)
    return "[" + "█" * filled + "░" * (bar_length - filled) + f"] {int(100 * current / total)}%"

client.run(BOT_TOKEN) 