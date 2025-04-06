import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Literal
import datetime
import logging

from bot.src.utils.permissions import is_admin

logger = logging.getLogger('moderation.aimod')

class AIModeration(commands.Cog):
    """AIモデレーション関連のコマンド"""
    
    def __init__(self, bot):
        self.bot = bot
    
    aimod_group = app_commands.Group(
        name="aimod",
        description="AI自動モデレーションの設定を管理します",
        default_permissions=discord.Permissions(administrator=True)
    )
    
    @aimod_group.command(name="status", description="AI自動モデレーションの状態を確認します")
    @is_admin()
    async def aimod_status(self, interaction: discord.Interaction):
        """AIモデレーションの状態を確認"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        # データベースから設定を取得
        settings = await ai_moderation.get_settings(interaction.guild.id)
        
        # 設定を表示するEmbedを作成
        embed = discord.Embed(
            title="🤖 AI自動モデレーション設定",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # 基本設定
        embed.add_field(
            name="有効状態",
            value=f"{'✅ 有効' if settings.get('enabled', False) else '❌ 無効'}",
            inline=True
        )
        
        # 毒性検出閾値
        toxicity_threshold = settings.get('toxicity_threshold', 0.8)
        embed.add_field(
            name="毒性検出閾値",
            value=f"{toxicity_threshold:.2f}",
            inline=True
        )
        
        # 検出時アクション
        action = settings.get('action_on_detection', 'warn')
        action_names = {
            'none': '何もしない',
            'warn': '警告のみ',
            'delete': 'メッセージ削除',
            'delete_warn': 'メッセージ削除+警告',
            'timeout': 'タイムアウト',
            'kick': 'キック',
            'ban': 'BAN'
        }
        embed.add_field(
            name="検出時アクション",
            value=action_names.get(action, '不明'),
            inline=True
        )
        
        # カスタム禁止ワード
        bad_words = settings.get('custom_bad_words', [])
        embed.add_field(
            name="カスタム禁止ワード",
            value=', '.join(bad_words) if bad_words else "設定なし",
            inline=False
        )
        
        # 除外チャンネル
        excluded_channels = settings.get('excluded_channels', [])
        excluded_roles = settings.get('excluded_roles', [])
        
        excluded_channels_text = []
        for channel_id in excluded_channels:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                excluded_channels_text.append(f"{channel.mention}")
        
        excluded_roles_text = []
        for role_id in excluded_roles:
            role = interaction.guild.get_role(role_id)
            if role:
                excluded_roles_text.append(f"{role.mention}")
        
        embed.add_field(
            name="除外チャンネル",
            value=', '.join(excluded_channels_text) if excluded_channels_text else "なし",
            inline=False
        )
        
        embed.add_field(
            name="除外ロール",
            value=', '.join(excluded_roles_text) if excluded_roles_text else "なし",
            inline=False
        )
        
        # 統計情報
        stats = settings.get('stats', {})
        if stats:
            detected_count = stats.get('detected_count', 0)
            actioned_count = stats.get('actioned_count', 0)
            
            embed.add_field(
                name="統計情報",
                value=f"検出回数: {detected_count}\nアクション実行回数: {actioned_count}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @aimod_group.command(name="toggle", description="AI自動モデレーションの有効/無効を切り替えます")
    @app_commands.describe(enabled="有効にするかどうか")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="有効", value="enable"),
        app_commands.Choice(name="無効", value="disable")
    ])
    @is_admin()
    async def aimod_toggle(
        self,
        interaction: discord.Interaction,
        enabled: str
    ):
        """AIモデレーションの有効/無効を切り替え"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        is_enabled = enabled == "enable"
        
        # データベースで設定を更新
        success = await ai_moderation.update_setting(interaction.guild.id, 'enabled', is_enabled)
        
        if success:
            await interaction.followup.send(f"✅ AI自動モデレーションを{'有効' if is_enabled else '無効'}にしました。")
        else:
            await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
    
    @aimod_group.command(name="threshold", description="毒性検出の閾値を設定します")
    @app_commands.describe(value="閾値（0.0〜1.0）- 高いほど厳格になります")
    @is_admin()
    async def aimod_threshold(
        self,
        interaction: discord.Interaction,
        value: float
    ):
        """毒性検出閾値の設定"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        # 閾値の範囲チェック
        if value < 0.0 or value > 1.0:
            await interaction.followup.send("⚠️ 閾値は0.0〜1.0の範囲で指定してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        # データベースで設定を更新
        success = await ai_moderation.update_setting(interaction.guild.id, 'toxicity_threshold', value)
        
        if success:
            await interaction.followup.send(f"✅ 毒性検出閾値を{value:.2f}に設定しました。")
        else:
            await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
    
    @aimod_group.command(name="action", description="有害コンテンツ検出時のアクションを設定します")
    @app_commands.describe(action="実行するアクション")
    @app_commands.choices(action=[
        app_commands.Choice(name="何もしない", value="none"),
        app_commands.Choice(name="警告のみ", value="warn"),
        app_commands.Choice(name="メッセージ削除", value="delete"),
        app_commands.Choice(name="メッセージ削除+警告", value="delete_warn"),
        app_commands.Choice(name="タイムアウト", value="timeout"),
        app_commands.Choice(name="キック", value="kick"),
        app_commands.Choice(name="BAN", value="ban")
    ])
    @is_admin()
    async def aimod_action(
        self,
        interaction: discord.Interaction,
        action: str
    ):
        """検出時アクションの設定"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        # データベースで設定を更新
        success = await ai_moderation.update_setting(interaction.guild.id, 'action_on_detection', action)
        
        # アクション名をわかりやすく変換
        action_names = {
            'none': '何もしない',
            'warn': '警告のみ',
            'delete': 'メッセージ削除',
            'delete_warn': 'メッセージ削除+警告',
            'timeout': 'タイムアウト',
            'kick': 'キック',
            'ban': 'BAN'
        }
        
        if success:
            await interaction.followup.send(f"✅ 検出時のアクションを「{action_names.get(action, action)}」に設定しました。")
        else:
            await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
    
    @aimod_group.command(name="badword", description="カスタム禁止ワードを追加または削除します")
    @app_commands.describe(
        action="追加または削除",
        word="禁止ワード"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="追加", value="add"),
        app_commands.Choice(name="削除", value="remove")
    ])
    @is_admin()
    async def aimod_badword(
        self,
        interaction: discord.Interaction,
        action: str,
        word: str
    ):
        """カスタム禁止ワードの管理"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        # 現在の禁止ワードリストを取得
        settings = await ai_moderation.get_settings(interaction.guild.id)
        bad_words = settings.get('custom_bad_words', [])
        
        if action == "add":
            # すでに存在する場合
            if word.lower() in [w.lower() for w in bad_words]:
                await interaction.followup.send(f"⚠️ 「{word}」はすでに禁止ワードリストに存在します。")
                return
            
            # 禁止ワードを追加
            bad_words.append(word)
            
            # データベースで設定を更新
            success = await ai_moderation.update_setting(interaction.guild.id, 'custom_bad_words', bad_words)
            
            if success:
                await interaction.followup.send(f"✅ 「{word}」を禁止ワードリストに追加しました。")
            else:
                await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
        
        elif action == "remove":
            # 存在しない場合
            if word.lower() not in [w.lower() for w in bad_words]:
                await interaction.followup.send(f"⚠️ 「{word}」は禁止ワードリストに存在しません。")
                return
            
            # 禁止ワードを削除（大文字小文字を区別せずに一致するものを削除）
            for i, w in enumerate(bad_words):
                if w.lower() == word.lower():
                    del bad_words[i]
                    break
            
            # データベースで設定を更新
            success = await ai_moderation.update_setting(interaction.guild.id, 'custom_bad_words', bad_words)
            
            if success:
                await interaction.followup.send(f"✅ 「{word}」を禁止ワードリストから削除しました。")
            else:
                await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
    
    @aimod_group.command(name="exclude", description="AIモデレーションから除外するチャンネルまたはロールを設定します")
    @app_commands.describe(
        type="除外するタイプ",
        action="追加または削除",
        channel="除外するチャンネル（typeがchannelの場合）",
        role="除外するロール（typeがroleの場合）"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="チャンネル", value="channel"),
        app_commands.Choice(name="ロール", value="role")
    ])
    @app_commands.choices(action=[
        app_commands.Choice(name="追加", value="add"),
        app_commands.Choice(name="削除", value="remove")
    ])
    @is_admin()
    async def aimod_exclude(
        self,
        interaction: discord.Interaction,
        type: str,
        action: str,
        channel: Optional[discord.TextChannel] = None,
        role: Optional[discord.Role] = None
    ):
        """除外チャンネル/ロールの管理"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        # パラメータの整合性チェック
        if type == "channel" and channel is None:
            await interaction.followup.send("⚠️ チャンネルを指定してください。")
            return
        elif type == "role" and role is None:
            await interaction.followup.send("⚠️ ロールを指定してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        settings = await ai_moderation.get_settings(interaction.guild.id)
        
        if type == "channel":
            # チャンネルの除外設定
            excluded_channels = settings.get('excluded_channels', [])
            
            if action == "add":
                # すでに除外されている場合
                if channel.id in excluded_channels:
                    await interaction.followup.send(f"⚠️ {channel.mention}はすでに除外リストに存在します。")
                    return
                
                # チャンネルを追加
                excluded_channels.append(channel.id)
                
                # データベースで設定を更新
                success = await ai_moderation.update_setting(interaction.guild.id, 'excluded_channels', excluded_channels)
                
                if success:
                    await interaction.followup.send(f"✅ {channel.mention}をAIモデレーションの除外リストに追加しました。")
                else:
                    await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
            
            elif action == "remove":
                # 除外されていない場合
                if channel.id not in excluded_channels:
                    await interaction.followup.send(f"⚠️ {channel.mention}は除外リストに存在しません。")
                    return
                
                # チャンネルを削除
                excluded_channels.remove(channel.id)
                
                # データベースで設定を更新
                success = await ai_moderation.update_setting(interaction.guild.id, 'excluded_channels', excluded_channels)
                
                if success:
                    await interaction.followup.send(f"✅ {channel.mention}をAIモデレーションの除外リストから削除しました。")
                else:
                    await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
        
        elif type == "role":
            # ロールの除外設定
            excluded_roles = settings.get('excluded_roles', [])
            
            if action == "add":
                # すでに除外されている場合
                if role.id in excluded_roles:
                    await interaction.followup.send(f"⚠️ {role.mention}はすでに除外リストに存在します。")
                    return
                
                # ロールを追加
                excluded_roles.append(role.id)
                
                # データベースで設定を更新
                success = await ai_moderation.update_setting(interaction.guild.id, 'excluded_roles', excluded_roles)
                
                if success:
                    await interaction.followup.send(f"✅ {role.mention}をAIモデレーションの除外リストに追加しました。")
                else:
                    await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
            
            elif action == "remove":
                # 除外されていない場合
                if role.id not in excluded_roles:
                    await interaction.followup.send(f"⚠️ {role.mention}は除外リストに存在しません。")
                    return
                
                # ロールを削除
                excluded_roles.remove(role.id)
                
                # データベースで設定を更新
                success = await ai_moderation.update_setting(interaction.guild.id, 'excluded_roles', excluded_roles)
                
                if success:
                    await interaction.followup.send(f"✅ {role.mention}をAIモデレーションの除外リストから削除しました。")
                else:
                    await interaction.followup.send("⚠️ 設定の更新中にエラーが発生しました。あとでもう一度お試しください。")
    
    @aimod_group.command(name="test", description="メッセージのAIモデレーションテストを行います")
    @app_commands.describe(message="テストするメッセージ内容")
    @is_admin()
    async def aimod_test(
        self,
        interaction: discord.Interaction,
        message: str
    ):
        """AIモデレーションのテスト"""
        await interaction.response.defer()
        
        # AIモデレーションモジュールの存在を確認
        if not hasattr(self.bot, 'manager') or not hasattr(self.bot.manager, 'ai_moderation'):
            await interaction.followup.send("⚠️ AIモデレーションモジュールが初期化されていません。管理者に連絡してください。")
            return
        
        ai_moderation = self.bot.manager.ai_moderation
        
        # AI分析を実行
        result = await ai_moderation.analyze_content(message)
        
        # 設定を取得して閾値を確認
        settings = await ai_moderation.get_settings(interaction.guild.id)
        threshold = settings.get('toxicity_threshold', 0.8)
        
        # 結果を表示するEmbedを作成
        embed = discord.Embed(
            title="🧪 AIモデレーションテスト",
            description=f"テスト対象: ```{message}```",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # AI分析結果
        if 'toxicity' in result:
            toxicity = result['toxicity']
            is_toxic = toxicity >= threshold
            
            embed.add_field(
                name="毒性スコア",
                value=f"{toxicity:.4f} / 1.0 {'⚠️ **検出**' if is_toxic else '✅ **安全**'}",
                inline=False
            )
            
            # 詳細スコア
            if 'categories' in result:
                categories = result['categories']
                for category, score in categories.items():
                    if score > 0.1:  # 小さすぎる値は表示しない
                        embed.add_field(
                            name=f"{category}",
                            value=f"{score:.4f}",
                            inline=True
                        )
        else:
            embed.add_field(
                name="エラー",
                value="AIによる分析が実行できませんでした。",
                inline=False
            )
        
        # 設定された禁止ワードのチェック
        bad_words = settings.get('custom_bad_words', [])
        detected_bad_words = []
        
        for word in bad_words:
            if word.lower() in message.lower():
                detected_bad_words.append(word)
        
        if detected_bad_words:
            embed.add_field(
                name="禁止ワード検出",
                value=", ".join(detected_bad_words),
                inline=False
            )
        
        # 実行されるアクション
        action = settings.get('action_on_detection', 'warn')
        action_names = {
            'none': '何もしない',
            'warn': '警告のみ',
            'delete': 'メッセージ削除',
            'delete_warn': 'メッセージ削除+警告',
            'timeout': 'タイムアウト',
            'kick': 'キック',
            'ban': 'BAN'
        }
        
        embed.add_field(
            name="実行されるアクション",
            value=f"{action_names.get(action, '不明')} {'(有害コンテンツと判定された場合)' if not is_toxic and not detected_bad_words else ''}",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AIModeration(bot)) 