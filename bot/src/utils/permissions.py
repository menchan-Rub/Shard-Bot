"""
権限管理ユーティリティ

このモジュールはDiscordの権限を管理するためのユーティリティ関数を提供します。
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union, List, Dict, Callable, Any
import logging
import enum
import functools

logger = logging.getLogger('utils.permissions')

# 権限レベルの定義
class PermissionLevel(enum.IntEnum):
    """権限レベル階層"""
    EVERYONE = 0      # 全員
    MODERATOR = 1     # モデレーター
    ADMIN = 2         # 管理者
    GUILD_OWNER = 3   # サーバーオーナー
    BOT_OWNER = 4     # ボットオーナー

# ロールIDと権限レベルのマッピングを保持するクラス
class PermissionManager:
    """サーバーごとの権限マッピングを管理するクラス"""
    
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {role_id: permission_level}}
        self._permission_cache = {}
        # {command_name: required_level}
        self._command_levels = {}
        # ボットオーナーID
        self._owner_ids = set()
        # デフォルトの権限設定
        self._setup_default_command_levels()
    
    def _setup_default_command_levels(self):
        """デフォルトのコマンド権限レベルを設定"""
        # モデレーションコマンド
        self.set_command_level("ban", PermissionLevel.MODERATOR)
        self.set_command_level("kick", PermissionLevel.MODERATOR)
        self.set_command_level("mute", PermissionLevel.MODERATOR)
        self.set_command_level("warn", PermissionLevel.MODERATOR)
        self.set_command_level("clear", PermissionLevel.MODERATOR)
        
        # 管理者コマンド
        self.set_command_level("settings", PermissionLevel.ADMIN)
        self.set_command_level("prefix", PermissionLevel.ADMIN)
        self.set_command_level("auto-response", PermissionLevel.ADMIN)
        self.set_command_level("aimod", PermissionLevel.ADMIN)
        self.set_command_level("raidmode", PermissionLevel.ADMIN)
        self.set_command_level("spamprotect", PermissionLevel.ADMIN)
        
        # ボットオーナーコマンド
        self.set_command_level("eval", PermissionLevel.BOT_OWNER)
        self.set_command_level("shutdown", PermissionLevel.BOT_OWNER)
        self.set_command_level("reload", PermissionLevel.BOT_OWNER)
    
    async def initialize(self):
        """データベースから権限設定を読み込む"""
        from bot.src.db.database import get_db_session
        from bot.src.db.models import GuildSettings
        
        async for session in get_db_session():
            try:
                # 全サーバーの権限設定を取得
                result = await session.execute(
                    "SELECT guild_id, role_permissions FROM guild_settings"
                )
                for guild_id, role_permissions in result:
                    if role_permissions:
                        self._permission_cache[guild_id] = role_permissions
                logger.info(f"Loaded permissions for {len(self._permission_cache)} guilds")
            except Exception as e:
                logger.error(f"Failed to load permissions: {e}")
    
    def set_owner_ids(self, owner_ids: List[int]):
        """ボットオーナーIDを設定"""
        self._owner_ids = set(owner_ids)
    
    def set_command_level(self, command_name: str, level: PermissionLevel):
        """コマンドに必要な権限レベルを設定"""
        self._command_levels[command_name] = level
    
    def get_command_level(self, command_name: str) -> PermissionLevel:
        """コマンドに必要な権限レベルを取得"""
        # サブコマンドの場合、親コマンド名を取得
        if ' ' in command_name:
            parent_command = command_name.split(' ')[0]
            if parent_command in self._command_levels:
                return self._command_levels[parent_command]
        
        return self._command_levels.get(command_name, PermissionLevel.EVERYONE)
    
    def set_role_level(self, guild_id: int, role_id: int, level: PermissionLevel):
        """ロールに権限レベルを設定"""
        if guild_id not in self._permission_cache:
            self._permission_cache[guild_id] = {}
        
        self._permission_cache[guild_id][role_id] = level
    
    def get_role_level(self, guild_id: int, role_id: int) -> PermissionLevel:
        """ロールの権限レベルを取得"""
        guild_perms = self._permission_cache.get(guild_id, {})
        return guild_perms.get(role_id, PermissionLevel.EVERYONE)
    
    async def get_user_level(self, user: discord.Member) -> PermissionLevel:
        """ユーザーの最高権限レベルを取得"""
        # ボットオーナーチェック
        if user.id in self._owner_ids:
            return PermissionLevel.BOT_OWNER
        
        # サーバーオーナーチェック
        if user.guild and user.id == user.guild.owner_id:
            return PermissionLevel.GUILD_OWNER
        
        # 管理者権限チェック
        if user.guild_permissions.administrator:
            return PermissionLevel.ADMIN
        
        # ロールベースの権限
        max_level = PermissionLevel.EVERYONE
        for role in user.roles:
            role_level = self.get_role_level(user.guild.id, role.id)
            max_level = max(max_level, role_level)
        
        return max_level
    
    async def can_execute(self, command_name: str, user: discord.Member) -> bool:
        """ユーザーがコマンドを実行できるかチェック"""
        required_level = self.get_command_level(command_name)
        user_level = await self.get_user_level(user)
        
        return user_level >= required_level
    
    async def save_permissions(self, guild_id: int):
        """サーバーの権限設定をデータベースに保存"""
        from bot.src.db.database import get_db_session
        from bot.src.db.models import GuildSettings
        
        guild_perms = self._permission_cache.get(guild_id, {})
        
        async for session in get_db_session():
            try:
                await session.execute(
                    "UPDATE guild_settings SET role_permissions = :perms WHERE guild_id = :guild_id",
                    {"perms": guild_perms, "guild_id": guild_id}
                )
                await session.commit()
                logger.info(f"Saved permissions for guild {guild_id}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save permissions for guild {guild_id}: {e}")

# 権限レベルチェックデコレータ
def has_permission_level(level: PermissionLevel):
    """指定した権限レベル以上が必要なデコレータ"""
    async def predicate(interaction: discord.Interaction) -> bool:
        # ボットからPermissionManagerを取得
        if not hasattr(interaction.client, 'permissions'):
            # フォールバック: Discordのデフォルト権限チェック
            if level == PermissionLevel.BOT_OWNER:
                return await interaction.client.is_owner(interaction.user)
            elif level == PermissionLevel.GUILD_OWNER:
                return interaction.guild.owner_id == interaction.user.id
            elif level == PermissionLevel.ADMIN:
                return interaction.user.guild_permissions.administrator
            elif level == PermissionLevel.MODERATOR:
                return (interaction.user.guild_permissions.ban_members or 
                        interaction.user.guild_permissions.kick_members or
                        interaction.user.guild_permissions.manage_messages)
            return True
        
        # PermissionManagerを使用して権限チェック
        perm_manager = interaction.client.permissions
        user_level = await perm_manager.get_user_level(interaction.user)
        
        if user_level < level:
            # 権限不足メッセージ
            level_names = {
                PermissionLevel.EVERYONE: "一般ユーザー",
                PermissionLevel.MODERATOR: "モデレーター",
                PermissionLevel.ADMIN: "管理者",
                PermissionLevel.GUILD_OWNER: "サーバーオーナー",
                PermissionLevel.BOT_OWNER: "ボットオーナー"
            }
            
            await interaction.response.send_message(
                f"このコマンドを実行するには{level_names[level]}権限が必要です。",
                ephemeral=True
            )
            return False
            
        return True
    
    return app_commands.check(predicate)

# ボットオーナーチェック
def is_owner():
    """ボットオーナーのみ実行可能なデコレータ"""
    return has_permission_level(PermissionLevel.BOT_OWNER)

# サーバーオーナーチェック
def is_guild_owner():
    """サーバーオーナーのみ実行可能なデコレータ"""
    return has_permission_level(PermissionLevel.GUILD_OWNER)

# 管理者チェック
def is_admin():
    """管理者のみ実行可能なデコレータ"""
    return has_permission_level(PermissionLevel.ADMIN)

# モデレーターチェック
def is_moderator():
    """モデレーターのみ実行可能なデコレータ"""
    return has_permission_level(PermissionLevel.MODERATOR) 