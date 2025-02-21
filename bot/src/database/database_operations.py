from typing import Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.future import select as future_select
from .models import Guild, User, Warning, SpamLog, Timer, CustomCommand, AutoMod, AuditLog, SupportTicket
import logging
from sqlalchemy import or_

logger = logging.getLogger('database_operations')

class DatabaseOperations:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Guild操作
    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """ギルド情報を取得します"""
        result = await self.session.execute(select(Guild).filter(Guild.id == guild_id))
        return result.scalar_one_or_none()

    async def create_guild(self, guild_id: int, **kwargs) -> Guild:
        """ギルド情報を作成します"""
        guild = Guild(id=guild_id, **kwargs)
        self.session.add(guild)
        await self.session.commit()
        return guild

    async def update_guild(self, guild_id: int, **kwargs) -> bool:
        """ギルド情報を更新します"""
        try:
            await self.session.execute(
                update(Guild)
                .where(Guild.id == guild_id)
                .values(**kwargs)
            )
            await self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update guild {guild_id}: {e}")
            return False

    # User操作
    async def get_user(self, user_id: int) -> Optional[User]:
        """ユーザー情報を取得します"""
        result = await self.session.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, user_id: int, **kwargs) -> User:
        """ユーザー情報を作成します"""
        user = User(id=user_id, **kwargs)
        self.session.add(user)
        await self.session.commit()
        return user

    # Warning操作
    async def add_warning(self, user_id: int, guild_id: int, moderator_id: int, reason: str) -> Warning:
        """警告を追加します"""
        warning = Warning(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            reason=reason
        )
        self.session.add(warning)
        await self.session.commit()
        return warning

    async def get_warnings(self, user_id: int, guild_id: int) -> List[Warning]:
        """ユーザーの警告履歴を取得します"""
        result = await self.session.execute(
            select(Warning)
            .filter(Warning.user_id == user_id)
            .filter(Warning.guild_id == guild_id)
        )
        return result.scalars().all()

    # SpamLog操作
    async def log_spam(self, user_id: int, guild_id: int, channel_id: int,
                      message_content: str, detection_type: str, action_taken: str) -> SpamLog:
        """スパム検出ログを記録します"""
        spam_log = SpamLog(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            message_content=message_content,
            detection_type=detection_type,
            action_taken=action_taken
        )
        self.session.add(spam_log)
        await self.session.commit()
        return spam_log

    # Timer操作
    async def create_timer(self, guild_id: int, channel_id: int, user_id: int,
                         expires_at: Any, message: str, is_recurring: bool = False,
                         interval: Optional[int] = None) -> Timer:
        """タイマーを作成します"""
        timer = Timer(
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            expires_at=expires_at,
            message=message,
            is_recurring=is_recurring,
            interval=interval
        )
        self.session.add(timer)
        await self.session.commit()
        return timer

    async def get_expired_timers(self) -> List[Timer]:
        """期限切れのタイマーを取得します"""
        from datetime import datetime
        result = await self.session.execute(
            select(Timer).filter(Timer.expires_at <= datetime.utcnow())
        )
        return result.scalars().all()

    # CustomCommand操作
    async def create_custom_command(self, guild_id: int, name: str,
                                  response: str, created_by: int) -> CustomCommand:
        """カスタムコマンドを作成します"""
        command = CustomCommand(
            guild_id=guild_id,
            name=name,
            response=response,
            created_by=created_by
        )
        self.session.add(command)
        await self.session.commit()
        return command

    async def get_custom_commands(self, guild_id: int) -> List[CustomCommand]:
        """ギルドのカスタムコマンドを取得します"""
        result = await self.session.execute(
            select(CustomCommand).filter(CustomCommand.guild_id == guild_id)
        )
        return result.scalars().all()

    # AutoMod操作
    async def create_automod_rule(self, guild_id: int, rule_type: str,
                                rule_data: Dict[str, Any], action: str) -> AutoMod:
        """自動モデレーションルールを作成します"""
        rule = AutoMod(
            guild_id=guild_id,
            rule_type=rule_type,
            rule_data=rule_data,
            action=action
        )
        self.session.add(rule)
        await self.session.commit()
        return rule

    async def get_automod_rules(self, guild_id: int) -> List[AutoMod]:
        """ギルドの自動モデレーションルールを取得します"""
        result = await self.session.execute(
            select(AutoMod)
            .filter(AutoMod.guild_id == guild_id)
            .filter(AutoMod.is_enabled == True)
        )
        return result.scalars().all()

    # AuditLog操作
    async def create_audit_log(self, guild_id: int, action_type: str,
                             user_id: int, target_id: int,
                             reason: str, details: Dict[str, Any]) -> AuditLog:
        """監査ログを作成します"""
        audit_log = AuditLog(
            guild_id=guild_id,
            action_type=action_type,
            user_id=user_id,
            target_id=target_id,
            reason=reason,
            details=details
        )
        self.session.add(audit_log)
        await self.session.commit()
        return audit_log

    async def get_audit_logs(self, guild_id: int, limit: int = 100) -> List[AuditLog]:
        """ギルドの監査ログを取得します"""
        result = await self.session.execute(
            select(AuditLog)
            .filter(AuditLog.guild_id == guild_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_support_ticket(
        self,
        user_id: int,
        guild_id: int,
        channel_id: int,
        admin_channel_id: int,
        webhook1_url: str,
        webhook2_url: str,
        name: str,
        service: str,
        is_bug: bool,
        severity: str
    ) -> SupportTicket:
        """サポートチケットを作成"""
        ticket = SupportTicket(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            admin_channel_id=admin_channel_id,
            webhook1_url=webhook1_url,
            webhook2_url=webhook2_url,
            name=name,
            service=service,
            is_bug=is_bug,
            severity=severity
        )
        self.session.add(ticket)
        await self.session.commit()
        return ticket

    async def get_support_ticket_by_channel(self, channel_id: int) -> Optional[SupportTicket]:
        """チャンネルIDからサポートチケットを取得"""
        query = select(SupportTicket).where(
            or_(
                SupportTicket.channel_id == channel_id,
                SupportTicket.admin_channel_id == channel_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_support_ticket_status(
        self,
        ticket_id: int,
        status: str
    ) -> Optional[SupportTicket]:
        """サポートチケットのステータスを更新"""
        query = select(SupportTicket).where(SupportTicket.id == ticket_id)
        result = await self.session.execute(query)
        ticket = result.scalar_one_or_none()
        
        if ticket:
            ticket.status = status
            await self.session.commit()
            
        return ticket 