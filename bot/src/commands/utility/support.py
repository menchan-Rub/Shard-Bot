import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any
import os
from database.database_connection import get_db
from database.database_operations import DatabaseOperations
import aiohttp
import io

class SupportModal(discord.ui.Modal, title="サポートチケット"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        
        self.name = discord.ui.TextInput(
            label="名前",
            placeholder="あなたの名前を入力してください",
            required=True,
            max_length=50
        )
        self.add_item(self.name)
        
        self.service = discord.ui.TextInput(
            label="サービス名",
            placeholder="対象のサービス名を入力してください",
            required=True,
            max_length=100
        )
        self.add_item(self.service)
        
        self.is_bug = discord.ui.Select(
            placeholder="バグ報告ですか？",
            options=[
                discord.SelectOption(label="はい", value="yes"),
                discord.SelectOption(label="いいえ", value="no")
            ]
        )
        
        self.severity = discord.ui.Select(
            placeholder="重要度を選択してください",
            options=[
                discord.SelectOption(label="高", value="high"),
                discord.SelectOption(label="中", value="medium"),
                discord.SelectOption(label="低", value="low")
            ]
        )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # サポートカテゴリーを取得または作成
            category = discord.utils.get(interaction.guild.categories, name="Support")
            if not category:
                category = await interaction.guild.create_category("Support")
            
            # チケットチャンネルを作成
            channel_name = f"{interaction.user.name}-ticket"
            ticket_channel = await category.create_text_channel(channel_name)
            
            # 管理サーバーの情報を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(interaction.guild.id)
                support_guild_id = guild_data.support_guild_id
                support_category_id = guild_data.support_category_id
            
            # 管理サーバーのカテゴリーを取得
            support_guild = self.bot.get_guild(support_guild_id)
            support_category = support_guild.get_channel(support_category_id)
            
            # 管理サーバーにチャンネルを作成
            admin_channel = await support_category.create_text_channel(channel_name)
            
            # Webhookを作成して相互に接続
            webhook1 = await ticket_channel.create_webhook(name=f"Support-{channel_name}")
            webhook2 = await admin_channel.create_webhook(name=f"Support-{channel_name}")
            
            # データベースにWebhook情報を保存
            await db.create_support_ticket(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                channel_id=ticket_channel.id,
                admin_channel_id=admin_channel.id,
                webhook1_url=webhook1.url,
                webhook2_url=webhook2.url,
                name=str(self.name),
                service=str(self.service),
                is_bug=self.is_bug.values[0],
                severity=self.severity.values[0]
            )
            
            # 管理パネルを送信
            embed = discord.Embed(
                title="サポートチケット情報",
                color=discord.Color.blue()
            )
            embed.add_field(name="ユーザー", value=interaction.user.mention, inline=False)
            embed.add_field(name="名前", value=str(self.name), inline=False)
            embed.add_field(name="サービス", value=str(self.service), inline=False)
            embed.add_field(name="バグ報告", value="はい" if self.is_bug.values[0] == "yes" else "いいえ", inline=False)
            embed.add_field(name="重要度", value=self.severity.values[0], inline=False)
            
            await admin_channel.send(embed=embed)
            
            # チケットチャンネルに初期メッセージを送信
            await ticket_channel.send(
                f"{interaction.user.mention} サポートチケットを作成しました。\n"
                "スタッフが対応するまでお待ちください。"
            )
            
            await interaction.response.send_message(
                f"チケットを作成しました: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            self.bot.logger.error(f"Error creating support ticket: {e}")
            await interaction.response.send_message(
                "チケットの作成中にエラーが発生しました。",
                ephemeral=True
            )

class SupportView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="サポートチケットを作成",
        style=discord.ButtonStyle.primary,
        custom_id="create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        modal = SupportModal(self.bot)
        await interaction.response.send_modal(modal)

class Support(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="support", description="サポートパネルを作成します")
    @app_commands.describe(password="管理者パスワード")
    @app_commands.guild_only()
    async def support(
        self,
        interaction: discord.Interaction,
        password: str
    ):
        try:
            # パスワードの検証
            if password != os.getenv('SETUP_PASSWORD'):
                await interaction.response.send_message(
                    "パスワードが正しくありません。",
                    ephemeral=True
                )
                return
            
            # 管理者権限の確認
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "このコマンドは管理者のみが使用できます。",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="サポートチケット",
                description="サポートが必要な場合は、下のボタンをクリックしてチケットを作成してください。",
                color=discord.Color.blue()
            )
            
            view = SupportView(self.bot)
            await interaction.channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                "サポートパネルを作成しました。",
                ephemeral=True
            )
            
        except Exception as e:
            self.bot.logger.error(f"Error creating support panel: {e}")
            await interaction.response.send_message(
                "サポートパネルの作成中にエラーが発生しました。",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージを相互に転送"""
        if message.author.bot or not message.guild:
            return
            
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                ticket = await db.get_support_ticket_by_channel(message.channel.id)
                
                if not ticket:
                    return
                
                # メッセージを転送
                webhook_url = ticket.webhook2_url if message.channel.id == ticket.channel_id else ticket.webhook1_url
                
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(webhook_url, session=session)
                    
                    # 添付ファイルを処理
                    files = []
                    for attachment in message.attachments:
                        file_data = await attachment.read()
                        files.append(
                            discord.File(
                                io.BytesIO(file_data),
                                filename=attachment.filename
                            )
                        )
                    
                    # メッセージを送信
                    await webhook.send(
                        content=message.content,
                        username=message.author.display_name,
                        avatar_url=message.author.avatar.url if message.author.avatar else None,
                        files=files
                    )
                    
        except Exception as e:
            self.bot.logger.error(f"Error forwarding message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Support(bot)) 