from typing import Dict, List, Set, Optional, Tuple
import discord
from discord.ext import commands
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
import re
from database.database_connection import get_db
from database.database_operations import DatabaseOperations
from config import RAID_PROTECTION

logger = logging.getLogger('moderation.raid_detection')

class RaidDetector:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 参加履歴を保持する辞書
        # {guild_id: deque([join_timestamps])}
        self.join_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
        # 新規アカウントの追跡
        # {guild_id: {user_id: join_timestamp}}
        self.new_accounts: Dict[int, Dict[int, datetime]] = defaultdict(dict)
        # 同一IPからの参加を検出するための辞書
        # {guild_id: {ip_hash: set(user_ids)}}
        self.ip_tracking: Dict[int, Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))
        # 不審なパターン
        self.suspicious_patterns = [re.compile(pattern) for pattern in RAID_PROTECTION['suspicious_patterns']]

    async def check_member_join(self, member: discord.Member) -> Tuple[bool, str, str]:
        """
        新規メンバーの参加をチェックし、レイドの可能性を判定します
        
        Returns
        -------
        Tuple[bool, str, str]
            (is_raid, detection_type, action)
        """
        if not member.guild:
            return False, "", ""

        # ギルド設定を取得
        async for session in get_db():
            db = DatabaseOperations(session)
            guild_data = await db.get_guild(member.guild.id)
            if not guild_data or not guild_data.raid_protection:
                return False, "", ""

        is_raid = False
        detection_type = ""
        action = ""

        # アカウント作成日時チェック
        if await self._check_account_age(member):
            is_raid = True
            detection_type = "new_account"
            action = "kick"

        # 短時間での大量参加チェック
        if await self._check_join_rate(member):
            is_raid = True
            detection_type = "mass_join"
            action = "lockdown"

        # 不審なパターンチェック
        if await self._check_suspicious_patterns(member):
            is_raid = True
            detection_type = "suspicious_pattern"
            action = "ban"

        # レイドを検出した場合、データベースに記録
        if is_raid:
            await self._log_raid(member, detection_type, action)

        return is_raid, detection_type, action

    async def _check_account_age(self, member: discord.Member) -> bool:
        """アカウントの作成日時をチェック"""
        account_age = datetime.utcnow() - member.created_at
        if account_age.days < RAID_PROTECTION['new_account_threshold']:
            self.new_accounts[member.guild.id][member.id] = datetime.utcnow()
            return True
        return False

    async def _check_join_rate(self, member: discord.Member) -> bool:
        """参加レートをチェック"""
        guild_id = member.guild.id
        now = datetime.utcnow()

        # 参加履歴を更新
        self.join_history[guild_id].append(now)

        # 設定された時間内の参加数をカウント
        recent_joins = [
            ts for ts in self.join_history[guild_id]
            if (now - ts).total_seconds() <= RAID_PROTECTION['join_rate_time']
        ]

        return len(recent_joins) > RAID_PROTECTION['join_rate_limit']

    async def _check_suspicious_patterns(self, member: discord.Member) -> bool:
        """不審なパターンをチェック"""
        # ユーザー名とニックネームをチェック
        text_to_check = f"{member.name}#{member.discriminator}"
        if member.nick:
            text_to_check += f" {member.nick}"

        return any(pattern.search(text_to_check) for pattern in self.suspicious_patterns)

    async def _log_raid(self, member: discord.Member, detection_type: str, action: str):
        """レイド検出をデータベースに記録"""
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=member.guild.id,
                    action_type="raid_detection",
                    user_id=member.id,
                    target_id=member.guild.id,
                    reason=f"レイド検出: {detection_type}",
                    details={
                        "detection_type": detection_type,
                        "action_taken": action,
                        "account_age": (datetime.utcnow() - member.created_at).days
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log raid: {e}")

    async def take_action(self, member: discord.Member, detection_type: str, action: str):
        """
        検出されたレイドに対してアクションを実行
        """
        try:
            if action == "kick":
                await member.kick(reason=f"レイド対策: {detection_type}")
                
            elif action == "ban":
                await member.ban(
                    reason=f"レイド対策: {detection_type}",
                    delete_message_days=1
                )
                
            elif action == "lockdown":
                # サーバーをロックダウン
                guild_data = None
                async for session in get_db():
                    db = DatabaseOperations(session)
                    guild_data = await db.get_guild(member.guild.id)

                if guild_data:
                    # 全チャンネルの権限を変更
                    for channel in member.guild.channels:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            await channel.set_permissions(
                                member.guild.default_role,
                                send_messages=False,
                                speak=False,
                                reason="レイド対策: サーバーロックダウン"
                            )

                    # ログチャンネルに通知
                    if guild_data.log_channel_id:
                        log_channel = member.guild.get_channel(guild_data.log_channel_id)
                        if log_channel:
                            embed = discord.Embed(
                                title="サーバーロックダウン",
                                description="レイド対策のため、サーバーをロックダウンしました。",
                                color=discord.Color.red()
                            )
                            embed.add_field(
                                name="検出タイプ",
                                value=detection_type,
                                inline=False
                            )
                            await log_channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to take action against raid: {e}")

    def cleanup_history(self):
        """
        古い履歴データを削除
        """
        now = datetime.utcnow()
        
        # 参加履歴のクリーンアップ
        for guild_id in list(self.join_history.keys()):
            # 24時間以上前の参加履歴を削除
            self.join_history[guild_id] = deque(
                [ts for ts in self.join_history[guild_id]
                 if (now - ts).total_seconds() <= 86400],
                maxlen=50
            )
            
            # 履歴が空の場合、ギルドのエントリを削除
            if not self.join_history[guild_id]:
                del self.join_history[guild_id]

        # 新規アカウント追跡のクリーンアップ
        for guild_id in list(self.new_accounts.keys()):
            for user_id in list(self.new_accounts[guild_id].keys()):
                # 7日以上前の記録を削除
                if (now - self.new_accounts[guild_id][user_id]).days >= 7:
                    del self.new_accounts[guild_id][user_id]
            
            # 記録が空の場合、ギルドのエントリを削除
            if not self.new_accounts[guild_id]:
                del self.new_accounts[guild_id]

    async def start_cleanup_task(self):
        """
        定期的なクリーンアップタスクを開始
        """
        while True:
            await asyncio.sleep(3600)  # 1時間ごとにクリーンアップ
            self.cleanup_history() 