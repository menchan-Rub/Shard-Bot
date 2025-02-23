import discord
from discord.ext import commands
from typing import List, Optional, Dict, Union, Tuple
import logging
from datetime import datetime, timedelta
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.member')

class MemberService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_member_info(self, member: discord.Member) -> Dict:
        """
        メンバーの情報を取得します。
        """
        try:
            # 基本情報を取得
            info = {
                'name': str(member),
                'id': member.id,
                'nick': member.nick,
                'created_at': member.created_at,
                'joined_at': member.joined_at,
                'roles': [role.name for role in member.roles[1:]],  # @everyoneを除外
                'color': str(member.color),
                'top_role': member.top_role.name,
                'guild_permissions': [perm[0] for perm in member.guild_permissions if perm[1]],
                'status': str(member.status),
                'is_on_mobile': member.is_on_mobile(),
                'avatar_url': str(member.display_avatar.url),
                'bot': member.bot
            }

            # アクティビティ情報
            if member.activity:
                info['activity'] = {
                    'type': str(member.activity.type),
                    'name': member.activity.name
                }

            # データベースから警告履歴を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                warnings = await db.get_warnings(member.id, member.guild.id)
                info['warning_count'] = len(warnings)

            return info

        except Exception as e:
            logger.error(f"Failed to get member info: {e}")
            raise

    async def kick_member(
        self,
        member: discord.Member,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーをキックします。
        """
        try:
            # キックを実行
            await member.kick(reason=f"{reason} (実行者: {moderator})" if reason else f"実行者: {moderator}")

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="kick",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={}
                )

            return "メンバーをキックしました。"

        except discord.Forbidden:
            return "キックの権限がありません。"
        except Exception as e:
            logger.error(f"Failed to kick member: {e}")
            return "キックの実行中にエラーが発生しました。"

    async def ban_member(
        self,
        member: discord.Member,
        delete_message_days: int = 1,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーをBANします。
        """
        try:
            # BANを実行
            await member.ban(
                delete_message_days=delete_message_days,
                reason=f"{reason} (実行者: {moderator})" if reason else f"実行者: {moderator}"
            )

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="ban",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={'delete_message_days': delete_message_days}
                )

            return "メンバーをBANしました。"

        except discord.Forbidden:
            return "BANの権限がありません。"
        except Exception as e:
            logger.error(f"Failed to ban member: {e}")
            return "BANの実行中にエラーが発生しました。"

    async def unban_member(
        self,
        guild: discord.Guild,
        user_id: int,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーのBANを解除します。
        """
        try:
            # BANリストからユーザーを取得
            ban_entry = await guild.fetch_ban(discord.Object(id=user_id))
            if not ban_entry:
                return "指定されたユーザーはBANされていません。"

            # BAN解除を実行
            await guild.unban(
                ban_entry.user,
                reason=f"{reason} (実行者: {moderator})" if reason else f"実行者: {moderator}"
            )

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=guild.id,
                    action_type="unban",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=user_id,
                    reason=reason,
                    details={}
                )

            return "メンバーのBANを解除しました。"

        except discord.NotFound:
            return "指定されたユーザーはBANされていません。"
        except discord.Forbidden:
            return "BAN解除の権限がありません。"
        except Exception as e:
            logger.error(f"Failed to unban member: {e}")
            return "BAN解除の実行中にエラーが発生しました。"

    async def timeout_member(
        self,
        member: discord.Member,
        duration: int,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーをタイムアウトします。
        """
        try:
            # タイムアウトを実行
            until = discord.utils.utcnow() + timedelta(seconds=duration)
            await member.timeout(
                until,
                reason=f"{reason} (実行者: {moderator})" if reason else f"実行者: {moderator}"
            )

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="timeout",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={'duration': duration}
                )

            return "メンバーをタイムアウトしました。"

        except discord.Forbidden:
            return "タイムアウトの権限がありません。"
        except Exception as e:
            logger.error(f"Failed to timeout member: {e}")
            return "タイムアウトの実行中にエラーが発生しました。"

    async def remove_timeout(
        self,
        member: discord.Member,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーのタイムアウトを解除します。
        """
        try:
            # タイムアウトを解除
            await member.timeout(
                None,
                reason=f"{reason} (実行者: {moderator})" if reason else f"実行者: {moderator}"
            )

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="remove_timeout",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={}
                )

            return "メンバーのタイムアウトを解除しました。"

        except discord.Forbidden:
            return "タイムアウト解除の権限がありません。"
        except Exception as e:
            logger.error(f"Failed to remove timeout: {e}")
            return "タイムアウト解除の実行中にエラーが発生しました。"

    async def warn_member(
        self,
        member: discord.Member,
        reason: str,
        moderator: discord.Member = None
    ) -> Tuple[str, int]:
        """
        メンバーに警告を付与します。
        """
        try:
            # 警告を追加
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.add_warning(
                    user_id=member.id,
                    guild_id=member.guild.id,
                    moderator_id=moderator.id if moderator else self.bot.user.id,
                    reason=reason
                )

                # 警告回数を取得
                warnings = await db.get_warnings(member.id, member.guild.id)
                warning_count = len(warnings)

            return "メンバーに警告を付与しました。", warning_count

        except Exception as e:
            logger.error(f"Failed to warn member: {e}")
            return "警告の付与中にエラーが発生しました。", 0

    async def get_warnings(
        self,
        member: discord.Member
    ) -> List[Dict]:
        """
        メンバーの警告履歴を取得します。
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                warnings = await db.get_warnings(member.id, member.guild.id)

                warning_list = []
                for warning in warnings:
                    moderator = member.guild.get_member(warning.moderator_id)
                    warning_list.append({
                        'id': warning.id,
                        'moderator': moderator.display_name if moderator else "不明",
                        'reason': warning.reason,
                        'created_at': warning.created_at
                    })

                return warning_list

        except Exception as e:
            logger.error(f"Failed to get warnings: {e}")
            return []

    async def clear_warnings(
        self,
        member: discord.Member,
        reason: Optional[str] = None,
        moderator: discord.Member = None
    ) -> str:
        """
        メンバーの警告をすべて削除します。
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                # 警告を削除
                await session.execute(
                    f"DELETE FROM warnings WHERE user_id = {member.id} AND guild_id = {member.guild.id}"
                )
                await session.commit()

                # 監査ログに記録
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="clear_warnings",
                    user_id=moderator.id if moderator else self.bot.user.id,
                    target_id=member.id,
                    reason=reason,
                    details={}
                )

            return "メンバーの警告をすべて削除しました。"

        except Exception as e:
            logger.error(f"Failed to clear warnings: {e}")
            return "警告の削除中にエラーが発生しました。" 