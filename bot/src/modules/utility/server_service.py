import discord
from discord.ext import commands
from typing import List, Optional, Dict, Union, Tuple, Any
import logging
from datetime import datetime, timedelta
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.server')

class ServerService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_server_info(self, guild: discord.Guild) -> Dict:
        """
        サーバーの情報を取得します。
        """
        try:
            # 基本情報を取得
            info = {
                'name': guild.name,
                'id': guild.id,
                'owner': guild.owner,
                'created_at': guild.created_at,
                'member_count': guild.member_count,
                'channel_count': len(guild.channels),
                'role_count': len(guild.roles),
                'emoji_count': len(guild.emojis),
                'boost_level': guild.premium_tier,
                'boost_count': guild.premium_subscription_count,
                'features': guild.features,
                'icon_url': guild.icon.url if guild.icon else None,
                'banner_url': guild.banner.url if guild.banner else None,
                'description': guild.description,
                'verification_level': str(guild.verification_level),
                'explicit_content_filter': str(guild.explicit_content_filter),
                'default_notifications': str(guild.default_notifications),
                'afk_timeout': guild.afk_timeout,
                'afk_channel': guild.afk_channel.name if guild.afk_channel else None,
                'system_channel': guild.system_channel.name if guild.system_channel else None,
                'rules_channel': guild.rules_channel.name if guild.rules_channel else None,
                'public_updates_channel': guild.public_updates_channel.name if guild.public_updates_channel else None
            }

            # データベースから設定を取得
            async for session in get_db():
                db = DatabaseOperations(session)
                guild_data = await db.get_guild(guild.id)
                if guild_data:
                    info.update({
                        'prefix': guild_data.prefix,
                        'language': guild_data.language,
                        'mod_role': guild.get_role(guild_data.mod_role_id).name if guild_data.mod_role_id else None,
                        'admin_role': guild.get_role(guild_data.admin_role_id).name if guild_data.admin_role_id else None,
                        'log_channel': guild.get_channel(guild_data.log_channel_id).name if guild_data.log_channel_id else None,
                        'welcome_channel': guild.get_channel(guild_data.welcome_channel_id).name if guild_data.welcome_channel_id else None,
                        'welcome_message': guild_data.welcome_message,
                        'leave_message': guild_data.leave_message,
                        'spam_protection': guild_data.spam_protection,
                        'raid_protection': guild_data.raid_protection
                    })

            return info

        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            raise

    async def update_server_settings(
        self,
        guild: discord.Guild,
        settings: Dict[str, Any],
        reason: Optional[str] = None
    ) -> str:
        """
        サーバーの設定を更新します。
        """
        try:
            # Discordの設定を更新
            await guild.edit(
                name=settings.get('name', guild.name),
                description=settings.get('description', guild.description),
                afk_channel=settings.get('afk_channel', guild.afk_channel),
                afk_timeout=settings.get('afk_timeout', guild.afk_timeout),
                verification_level=settings.get('verification_level', guild.verification_level),
                default_notifications=settings.get('default_notifications', guild.default_notifications),
                explicit_content_filter=settings.get('explicit_content_filter', guild.explicit_content_filter),
                system_channel=settings.get('system_channel', guild.system_channel),
                system_channel_flags=settings.get('system_channel_flags', guild.system_channel_flags),
                reason=reason
            )

            # データベースの設定を更新
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.update_guild(
                    guild_id=guild.id,
                    prefix=settings.get('prefix'),
                    language=settings.get('language'),
                    mod_role_id=settings.get('mod_role_id'),
                    admin_role_id=settings.get('admin_role_id'),
                    log_channel_id=settings.get('log_channel_id'),
                    welcome_channel_id=settings.get('welcome_channel_id'),
                    welcome_message=settings.get('welcome_message'),
                    leave_message=settings.get('leave_message'),
                    spam_protection=settings.get('spam_protection'),
                    raid_protection=settings.get('raid_protection')
                )

            return "サーバー設定を更新しました。"

        except discord.Forbidden:
            return "サーバー設定の更新権限がありません。"
        except Exception as e:
            logger.error(f"Failed to update server settings: {e}")
            return "サーバー設定の更新中にエラーが発生しました。"

    async def create_invite(
        self,
        channel: discord.TextChannel,
        max_age: int = 0,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = True,
        reason: Optional[str] = None
    ) -> Tuple[discord.Invite, str]:
        """
        招待リンクを作成します。
        """
        try:
            invite = await channel.create_invite(
                max_age=max_age,
                max_uses=max_uses,
                temporary=temporary,
                unique=unique,
                reason=reason
            )

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="create_invite",
                    user_id=self.bot.user.id,
                    target_id=channel.id,
                    reason=reason or "招待リンクを作成",
                    details={
                        'code': invite.code,
                        'max_age': max_age,
                        'max_uses': max_uses,
                        'temporary': temporary
                    }
                )

            return invite, "招待リンクを作成しました。"

        except discord.Forbidden:
            return None, "招待リンクの作成権限がありません。"
        except Exception as e:
            logger.error(f"Failed to create invite: {e}")
            return None, "招待リンクの作成中にエラーが発生しました。"

    async def get_invites(self, guild: discord.Guild) -> List[discord.Invite]:
        """
        サーバーの招待リンク一覧を取得します。
        """
        try:
            return await guild.invites()
        except discord.Forbidden:
            logger.error("Missing permissions to get invites")
            return []
        except Exception as e:
            logger.error(f"Failed to get invites: {e}")
            return []

    async def delete_invite(
        self,
        invite: discord.Invite,
        reason: Optional[str] = None
    ) -> str:
        """
        招待リンクを削除します。
        """
        try:
            await invite.delete(reason=reason)

            # 監査ログに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=invite.guild.id,
                    action_type="delete_invite",
                    user_id=self.bot.user.id,
                    target_id=None,
                    reason=reason or "招待リンクを削除",
                    details={
                        'code': invite.code
                    }
                )

            return "招待リンクを削除しました。"

        except discord.Forbidden:
            return "招待リンクの削除権限がありません。"
        except Exception as e:
            logger.error(f"Failed to delete invite: {e}")
            return "招待リンクの削除中にエラーが発生しました。"

    async def get_audit_logs(
        self,
        guild: discord.Guild,
        limit: int = 100,
        action_type: Optional[str] = None,
        user: Optional[discord.Member] = None
    ) -> List[Dict]:
        """
        監査ログを取得します。
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                logs = await db.get_audit_logs(guild.id, limit)

                # フィルタリング
                filtered_logs = []
                for log in logs:
                    if action_type and log.action_type != action_type:
                        continue
                    if user and log.user_id != user.id:
                        continue
                    
                    # ユーザー情報を取得
                    actor = guild.get_member(log.user_id)
                    target = guild.get_member(log.target_id) if log.target_id else None

                    filtered_logs.append({
                        'id': log.id,
                        'action_type': log.action_type,
                        'actor': actor.display_name if actor else "不明",
                        'target': target.display_name if target else "不明",
                        'reason': log.reason,
                        'details': log.details,
                        'timestamp': log.created_at
                    })

                return filtered_logs

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return [] 