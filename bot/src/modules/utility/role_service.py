import discord
from discord.ext import commands
from typing import Dict, List, Optional, Tuple
import logging
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.role')

class RoleService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_role(
        self,
        guild: discord.Guild,
        name: str,
        color: Optional[discord.Color] = None,
        hoist: bool = False,
        mentionable: bool = False,
        permissions: discord.Permissions = discord.Permissions.none(),
        reason: Optional[str] = None
    ) -> Tuple[discord.Role, str]:
        """
        新しいロールを作成します。

        Parameters
        ----------
        guild : discord.Guild
            サーバー
        name : str
            ロール名
        color : discord.Color, optional
            ロールの色
        hoist : bool
            メンバーリストで別枠表示するかどうか
        mentionable : bool
            メンション可能かどうか
        permissions : discord.Permissions
            権限設定
        reason : str, optional
            作成理由

        Returns
        -------
        Tuple[discord.Role, str]
            作成されたロールと結果メッセージ
        """
        try:
            # ロールを作成
            role = await guild.create_role(
                name=name,
                color=color,
                hoist=hoist,
                mentionable=mentionable,
                permissions=permissions,
                reason=reason
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=guild.id,
                    action_type="role_create",
                    user_id=self.bot.user.id,
                    target_id=role.id,
                    reason=reason,
                    details={
                        'name': name,
                        'color': str(color) if color else None,
                        'hoist': hoist,
                        'mentionable': mentionable,
                        'permissions': permissions.value
                    }
                )

            return role, "ロールを作成しました。"

        except discord.Forbidden:
            raise ValueError("ロールの作成権限がありません。")
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            raise ValueError("ロールの作成に失敗しました。")

    async def delete_role(
        self,
        role: discord.Role,
        reason: Optional[str] = None
    ) -> str:
        """
        ロールを削除します。

        Parameters
        ----------
        role : discord.Role
            削除するロール
        reason : str, optional
            削除理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            role_id = role.id
            guild_id = role.guild.id

            # ロールを削除
            await role.delete(reason=reason)

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=guild_id,
                    action_type="role_delete",
                    user_id=self.bot.user.id,
                    target_id=role_id,
                    reason=reason,
                    details={}
                )

            return "ロールを削除しました。"

        except discord.Forbidden:
            raise ValueError("ロールの削除権限がありません。")
        except Exception as e:
            logger.error(f"Failed to delete role: {e}")
            raise ValueError("ロールの削除に失敗しました。")

    async def add_role(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: Optional[str] = None
    ) -> str:
        """
        メンバーにロールを付与します。

        Parameters
        ----------
        member : discord.Member
            対象メンバー
        role : discord.Role
            付与するロール
        reason : str, optional
            付与理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # ロールを付与
            await member.add_roles(role, reason=reason)

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="role_add",
                    user_id=self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={'role_id': role.id}
                )

            return f"{member.mention} にロール {role.name} を付与しました。"

        except discord.Forbidden:
            raise ValueError("ロールの付与権限がありません。")
        except Exception as e:
            logger.error(f"Failed to add role: {e}")
            raise ValueError("ロールの付与に失敗しました。")

    async def remove_role(
        self,
        member: discord.Member,
        role: discord.Role,
        reason: Optional[str] = None
    ) -> str:
        """
        メンバーからロールを削除します。

        Parameters
        ----------
        member : discord.Member
            対象メンバー
        role : discord.Role
            削除するロール
        reason : str, optional
            削除理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # ロールを削除
            await member.remove_roles(role, reason=reason)

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="role_remove",
                    user_id=self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={'role_id': role.id}
                )

            return f"{member.mention} からロール {role.name} を削除しました。"

        except discord.Forbidden:
            raise ValueError("ロールの削除権限がありません。")
        except Exception as e:
            logger.error(f"Failed to remove role: {e}")
            raise ValueError("ロールの削除に失敗しました。")

    async def modify_role(
        self,
        role: discord.Role,
        name: Optional[str] = None,
        color: Optional[discord.Color] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
        permissions: Optional[discord.Permissions] = None,
        reason: Optional[str] = None
    ) -> str:
        """
        ロールの設定を変更します。

        Parameters
        ----------
        role : discord.Role
            変更するロール
        name : str, optional
            新しいロール名
        color : discord.Color, optional
            新しい色
        hoist : bool, optional
            メンバーリストで別枠表示するかどうか
        mentionable : bool, optional
            メンション可能かどうか
        permissions : discord.Permissions, optional
            新しい権限設定
        reason : str, optional
            変更理由

        Returns
        -------
        str
            結果メッセージ
        """
        try:
            # 変更内容を記録
            changes = {}
            if name is not None and name != role.name:
                changes['name'] = {'old': role.name, 'new': name}
            if color is not None and color != role.color:
                changes['color'] = {'old': str(role.color), 'new': str(color)}
            if hoist is not None and hoist != role.hoist:
                changes['hoist'] = {'old': role.hoist, 'new': hoist}
            if mentionable is not None and mentionable != role.mentionable:
                changes['mentionable'] = {'old': role.mentionable, 'new': mentionable}
            if permissions is not None and permissions.value != role.permissions.value:
                changes['permissions'] = {'old': role.permissions.value, 'new': permissions.value}

            if not changes:
                return "変更する内容がありません。"

            # ロールを更新
            await role.edit(
                name=name if name is not None else role.name,
                color=color if color is not None else role.color,
                hoist=hoist if hoist is not None else role.hoist,
                mentionable=mentionable if mentionable is not None else role.mentionable,
                permissions=permissions if permissions is not None else role.permissions,
                reason=reason
            )

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=role.guild.id,
                    action_type="role_modify",
                    user_id=self.bot.user.id,
                    target_id=role.id,
                    reason=reason,
                    details=changes
                )

            return "ロールの設定を変更しました。"

        except discord.Forbidden:
            raise ValueError("ロールの変更権限がありません。")
        except Exception as e:
            logger.error(f"Failed to modify role: {e}")
            raise ValueError("ロールの変更に失敗しました。")

    async def list_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """
        サーバーのロール一覧を取得します。

        Parameters
        ----------
        guild : discord.Guild
            サーバー

        Returns
        -------
        List[discord.Role]
            ロールのリスト
        """
        try:
            return guild.roles
        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            raise ValueError("ロール一覧の取得に失敗しました。")

    async def get_role_info(self, role: discord.Role) -> Dict:
        """
        ロールの詳細情報を取得します。

        Parameters
        ----------
        role : discord.Role
            情報を取得するロール

        Returns
        -------
        Dict
            ロールの情報
        """
        try:
            return {
                'id': role.id,
                'name': role.name,
                'color': role.color,
                'hoist': role.hoist,
                'position': role.position,
                'managed': role.managed,
                'mentionable': role.mentionable,
                'permissions': role.permissions.value,
                'created_at': role.created_at,
                'member_count': len(role.members)
            }
        except Exception as e:
            logger.error(f"Failed to get role info: {e}")
            raise ValueError("ロール情報の取得に失敗しました。") 