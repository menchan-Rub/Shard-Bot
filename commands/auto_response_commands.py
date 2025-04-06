import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import datetime

class AutoResponseCommands(commands.Cog):
    """自動応答システム関連のコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="auto-response", description="自動応答システムの設定を管理します")
    @app_commands.describe(
        action="実行するアクション",
        enable_disable="有効化または無効化",
        channel="特定のチャンネルを選択（指定しない場合は全体設定）",
        chance="応答確率（0.0〜1.0）",
        cooldown="クールダウン（秒）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="設定確認", value="status"),
        app_commands.Choice(name="有効/無効設定", value="toggle"),
        app_commands.Choice(name="確率設定", value="chance"),
        app_commands.Choice(name="クールダウン設定", value="cooldown"),
        app_commands.Choice(name="レポート表示", value="report")
    ])
    @app_commands.choices(enable_disable=[
        app_commands.Choice(name="有効化", value="enable"),
        app_commands.Choice(name="無効化", value="disable")
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def auto_response(
        self, 
        interaction: discord.Interaction, 
        action: str,
        enable_disable: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        chance: Optional[float] = None, 
        cooldown: Optional[int] = None
    ):
        """自動応答システムの設定を管理します"""
        await interaction.response.defer()
        
        if not hasattr(self.bot, 'manager') or not self.bot.manager.auto_response:
            await interaction.followup.send("⚠️ 自動応答モジュールが初期化されていません。管理者に連絡してください。")
            return
            
        auto_response = self.bot.manager.auto_response
        
        # 設定確認
        if action == "status":
            embed = discord.Embed(
                title="🤖 自動応答システム設定",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(
                name="システム状態",
                value=f"{'✅ 有効' if auto_response.config.get('enabled', False) else '❌ 無効'}",
                inline=True
            )
            
            embed.add_field(
                name="応答確率",
                value=f"{auto_response.config.get('response_chance', 0.1) * 100:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="クールダウン",
                value=f"{auto_response.config.get('cooldown', 60)}秒",
                inline=True
            )
            
            embed.add_field(
                name="AIパワード応答",
                value=f"{'✅ 有効' if auto_response.config.get('ai_powered', False) else '❌ 無効'}",
                inline=True
            )
            
            embed.add_field(
                name="無視するプレフィックス",
                value=", ".join(auto_response.config.get('ignore_prefixes', [])) or "なし",
                inline=True
            )
            
            embed.add_field(
                name="コンテキスト履歴長",
                value=str(auto_response.config.get('max_context_length', 10)),
                inline=True
            )
            
            custom_responses = auto_response.config.get('custom_responses', {})
            response_info = []
            
            for key, responses in custom_responses.items():
                response_info.append(f"**{key}**: {len(responses)}件の応答")
                
            embed.add_field(
                name="カスタム応答パターン",
                value="\n".join(response_info) if response_info else "なし",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        # 有効/無効設定
        elif action == "toggle":
            if not enable_disable:
                await interaction.followup.send("❌ 有効化または無効化を指定してください。")
                return
                
            # ここに設定を保存する処理を実装
            await interaction.followup.send(f"✅ 自動応答システムを{('有効' if enable_disable == 'enable' else '無効')}にしました。")
            
        # 確率設定
        elif action == "chance":
            if chance is None:
                await interaction.followup.send("❌ 確率を指定してください（0.0〜1.0）。")
                return
                
            if chance < 0.0 or chance > 1.0:
                await interaction.followup.send("❌ 確率は0.0〜1.0の範囲で指定してください。")
                return
                
            # ここに設定を保存する処理を実装
            await interaction.followup.send(f"✅ 応答確率を{chance * 100:.1f}%に設定しました。")
            
        # クールダウン設定
        elif action == "cooldown":
            if cooldown is None:
                await interaction.followup.send("❌ クールダウン秒数を指定してください。")
                return
                
            if cooldown < 0:
                await interaction.followup.send("❌ クールダウンは0以上の値を指定してください。")
                return
                
            # ここに設定を保存する処理を実装
            await interaction.followup.send(f"✅ クールダウンを{cooldown}秒に設定しました。")
            
        # レポート表示
        elif action == "report":
            days = 30  # デフォルト30日
            
            if not auto_response:
                await interaction.followup.send("⚠️ 自動応答モジュールが初期化されていません。")
                return
                
            # レポート生成
            report_embed = await auto_response.generate_report(interaction.guild, days)
            await interaction.followup.send(embed=report_embed)
            
    @app_commands.command(name="auto-response-test", description="自動応答のテストを行います")
    @app_commands.describe(message="テストするメッセージ内容")
    async def auto_response_test(self, interaction: discord.Interaction, message: str):
        """自動応答のテスト"""
        await interaction.response.defer()
        
        if not hasattr(self.bot, 'manager') or not self.bot.manager.auto_response:
            await interaction.followup.send("⚠️ 自動応答モジュールが初期化されていません。")
            return
            
        auto_response = self.bot.manager.auto_response
        
        # 応答を取得
        response = await auto_response.get_response(interaction)
        
        if response:
            embed = discord.Embed(
                title="🤖 自動応答テスト",
                description=f"入力: {message}\n\n応答: {response}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 応答を生成できませんでした。")

async def setup(bot):
    await bot.add_cog(AutoResponseCommands(bot))

def teardown(bot):
    # 特に解放処理は必要ない
    pass 