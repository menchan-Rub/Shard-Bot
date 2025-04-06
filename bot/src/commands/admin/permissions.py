import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import datetime
import logging

from bot.src.utils.permissions import PermissionLevel, is_admin, is_guild_owner

logger = logging.getLogger('commands.admin.permissions')

class Permissions(commands.Cog):
    """権限管理コマンド"""
    
    def __init__(self, bot):
        self.bot = bot
    
    permissions_group = app_commands.Group(
        name="permissions",
        description="サーバー内の権限設定を管理します",
        default_permissions=discord.Permissions(administrator=True)
    )
    
    @permissions_group.command(name="view", description="現在の権限設定を表示します")
    @is_admin()
    async def permissions_view(self, interaction: discord.Interaction):
        """権限設定の表示"""
        if not hasattr(self.bot, 'permissions'):
            await interaction.response.send_message(
                "権限マネージャーが初期化されていません。",
                ephemeral=True
            )
            return
        
        perm_manager = self.bot.permissions
        
        # 権限設定を表示するEmbedを作成
        embed = discord.Embed(
            title="🔒 サーバー権限設定",
            description="このサーバーでの権限レベル設定です。",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # 権限レベルごとの説明
        level_descriptions = {
            PermissionLevel.EVERYONE: "すべてのユーザー",
            PermissionLevel.MODERATOR: "モデレーター（メッセージ管理、BANなどができる）",
            PermissionLevel.ADMIN: "管理者（サーバー設定の変更ができる）",
            PermissionLevel.GUILD_OWNER: "サーバーオーナー",
            PermissionLevel.BOT_OWNER: "ボットオーナー"
        }
        
        # 権限レベルの説明を追加
        embed.add_field(
            name="権限レベル説明",
            value="\n".join([f"**レベル{level}**: {desc}" for level, desc in level_descriptions.items()]),
            inline=False
        )
        
        # ロールの権限設定を取得
        guild_id = interaction.guild.id
        role_permissions = {}
        
        # サーバー内の全ロールを取得
        for role in interaction.guild.roles:
            level = perm_manager.get_role_level(guild_id, role.id)
            if level > PermissionLevel.EVERYONE:
                role_permissions[role.id] = level
        
        # ロールの権限設定を表示
        if role_permissions:
            roles_text = []
            for role_id, level in role_permissions.items():
                role = interaction.guild.get_role(role_id)
                if role:
                    roles_text.append(f"{role.mention}: レベル{level} ({level_descriptions[level]})")
            
            embed.add_field(
                name="ロール権限設定",
                value="\n".join(roles_text) if roles_text else "設定されていません",
                inline=False
            )
        else:
            embed.add_field(
                name="ロール権限設定",
                value="設定されていません",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @permissions_group.command(name="set", description="ロールの権限レベルを設定します")
    @app_commands.describe(
        role="権限レベルを設定するロール",
        level="設定する権限レベル（0: 一般, 1: モデレーター, 2: 管理者）"
    )
    @is_guild_owner()
    async def permissions_set(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        level: int
    ):
        """ロールに権限レベルを設定"""
        if not hasattr(self.bot, 'permissions'):
            await interaction.response.send_message(
                "権限マネージャーが初期化されていません。",
                ephemeral=True
            )
            return
        
        # レベルの妥当性チェック
        if level < 0 or level > 2:  # 一般ユーザー、モデレーター、管理者のみ設定可能
            await interaction.response.send_message(
                "権限レベルは0（一般）、1（モデレーター）、2（管理者）のいずれかを指定してください。",
                ephemeral=True
            )
            return
        
        # @everyoneロールに管理者権限を設定できないようにする
        if role.id == interaction.guild.id and level > 0:
            await interaction.response.send_message(
                "@everyoneロールにはモデレーターや管理者権限を設定できません。",
                ephemeral=True
            )
            return
        
        perm_manager = self.bot.permissions
        
        # 権限レベルを設定
        perm_level = PermissionLevel(level)
        perm_manager.set_role_level(interaction.guild.id, role.id, perm_level)
        
        # データベースに保存
        await perm_manager.save_permissions(interaction.guild.id)
        
        # レベル名の取得
        level_names = {
            PermissionLevel.EVERYONE: "一般ユーザー",
            PermissionLevel.MODERATOR: "モデレーター",
            PermissionLevel.ADMIN: "管理者"
        }
        
        # 成功メッセージ
        await interaction.response.send_message(
            f"✅ {role.mention}の権限レベルを{level_names[perm_level]}に設定しました。",
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @permissions_group.command(name="reset", description="ロールの権限レベルをリセットします")
    @app_commands.describe(role="権限レベルをリセットするロール")
    @is_guild_owner()
    async def permissions_reset(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """ロールの権限レベルをリセット"""
        if not hasattr(self.bot, 'permissions'):
            await interaction.response.send_message(
                "権限マネージャーが初期化されていません。",
                ephemeral=True
            )
            return
        
        perm_manager = self.bot.permissions
        
        # 権限レベルをリセット
        perm_manager.set_role_level(interaction.guild.id, role.id, PermissionLevel.EVERYONE)
        
        # データベースに保存
        await perm_manager.save_permissions(interaction.guild.id)
        
        # 成功メッセージ
        await interaction.response.send_message(
            f"✅ {role.mention}の権限レベルをリセットしました。",
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @permissions_group.command(name="test", description="ユーザーの現在の権限レベルをテストします")
    @app_commands.describe(user="テストするユーザー（指定しない場合は自分）")
    async def permissions_test(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """ユーザーの権限レベルをテスト"""
        if not hasattr(self.bot, 'permissions'):
            await interaction.response.send_message(
                "権限マネージャーが初期化されていません。",
                ephemeral=True
            )
            return
        
        # ユーザーが指定されていない場合は自分自身
        target_user = user or interaction.user
        
        perm_manager = self.bot.permissions
        
        # 権限レベルを取得
        user_level = await perm_manager.get_user_level(target_user)
        
        # レベル名の取得
        level_names = {
            PermissionLevel.EVERYONE: "一般ユーザー",
            PermissionLevel.MODERATOR: "モデレーター",
            PermissionLevel.ADMIN: "管理者",
            PermissionLevel.GUILD_OWNER: "サーバーオーナー",
            PermissionLevel.BOT_OWNER: "ボットオーナー"
        }
        
        # 結果を表示
        embed = discord.Embed(
            title="🔍 権限レベルテスト",
            description=f"{target_user.mention}の権限レベル",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="権限レベル",
            value=f"レベル{user_level} ({level_names[user_level]})",
            inline=False
        )
        
        # 権限の根拠を取得
        if user_level == PermissionLevel.BOT_OWNER:
            reason = "ボットオーナーとして登録されています"
        elif user_level == PermissionLevel.GUILD_OWNER:
            reason = "このサーバーのオーナーです"
        elif user_level == PermissionLevel.ADMIN:
            if target_user.guild_permissions.administrator:
                reason = "Discordの管理者権限を持っています"
            else:
                reason = "管理者レベルのロールが設定されています"
        elif user_level == PermissionLevel.MODERATOR:
            if (target_user.guild_permissions.ban_members or 
                target_user.guild_permissions.kick_members or 
                target_user.guild_permissions.manage_messages):
                reason = "Discordのモデレーター関連権限を持っています"
            else:
                reason = "モデレーターレベルのロールが設定されています"
        else:
            reason = "特別な権限は設定されていません"
        
        embed.add_field(
            name="権限の根拠",
            value=reason,
            inline=False
        )
        
        # ロールとそのレベルを表示
        roles_with_perms = []
        for role in target_user.roles:
            role_level = perm_manager.get_role_level(interaction.guild.id, role.id)
            if role_level > PermissionLevel.EVERYONE:
                roles_with_perms.append(f"{role.mention}: レベル{role_level} ({level_names[role_level]})")
        
        if roles_with_perms:
            embed.add_field(
                name="特別権限を持つロール",
                value="\n".join(roles_with_perms),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Permissions(bot)) 