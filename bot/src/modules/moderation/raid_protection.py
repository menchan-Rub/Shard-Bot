import discord
from discord.ext import commands
import asyncio
import logging
import time
from collections import deque
import aiohttp
from typing import Dict, List, Set, Any, Optional, Tuple

logger = logging.getLogger('ShardBot.RaidProtection')

class RaidProtection:
    """レイド保護機能を提供するクラス"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings_cache = {}  # guild_id: settings
        self.cache_expire = {}    # guild_id: timestamp
        
        # 参加履歴を保持
        self.join_history = {}  # {guild_id: deque(member, timestamp)}
        
        # アクティブなレイド検出
        self.active_raids = {}  # {guild_id: {'start_time': timestamp, 'count': int, 'members': set()}}
        
        # 設定キャッシュの定期的なクリーンアップタスク
        self.bot.loop.create_task(self._cache_cleanup_task())
        
        # レイド状態の定期的なクリーンアップタスク
        self.bot.loop.create_task(self._raid_cleanup_task())
    
    async def _cache_cleanup_task(self):
        """期限切れのキャッシュエントリを定期的にクリーンアップする"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                import time
                current_time = time.time()
                expired_guilds = [
                    guild_id for guild_id, expire_time in self.cache_expire.items()
                    if current_time > expire_time
                ]
                
                for guild_id in expired_guilds:
                    self.settings_cache.pop(guild_id, None)
                    self.cache_expire.pop(guild_id, None)
                
                if expired_guilds:
                    logger.debug(f"Cleaned up {len(expired_guilds)} expired cache entries")
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
            
            await asyncio.sleep(300)  # 5分ごとに実行
    
    async def _raid_cleanup_task(self):
        """古いレイド検出状態と参加履歴を定期的にクリーンアップする"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                current_time = time.time()
                
                # 古い参加履歴をクリーンアップ
                for guild_id in list(self.join_history.keys()):
                    # 1時間以上古い参加履歴をクリア
                    cutoff_time = current_time - 3600
                    while self.join_history[guild_id] and self.join_history[guild_id][0][1] < cutoff_time:
                        self.join_history[guild_id].popleft()
                    
                    # 空になった場合は削除
                    if not self.join_history[guild_id]:
                        del self.join_history[guild_id]
                
                # 古いレイド検出状態をクリーンアップ
                for guild_id in list(self.active_raids.keys()):
                    # 1時間以上継続しているレイド状態をクリア
                    if current_time - self.active_raids[guild_id]['start_time'] > 3600:
                        del self.active_raids[guild_id]
                        # サーバーにレイド終了を通知
                        guild = self.bot.get_guild(int(guild_id))
                        if guild:
                            try:
                                settings = await self.get_guild_settings(guild_id)
                                log_channel_id = settings.get("logChannelId")
                                if log_channel_id:
                                    log_channel = guild.get_channel(int(log_channel_id))
                                    if log_channel:
                                        await log_channel.send("🛡️ レイド警戒モードを解除しました。")
                            except Exception as e:
                                logger.error(f"Error sending raid end notification: {e}")
            except Exception as e:
                logger.error(f"Error in raid cleanup task: {e}")
            
            await asyncio.sleep(60)  # 1分ごとに実行
    
    async def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """ギルドのレイド保護設定を取得する"""
        # キャッシュをチェック
        if guild_id in self.settings_cache:
            return self.settings_cache[guild_id]
        
        try:
            # データベースから設定を取得
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://api:8000/settings?guild_id={guild_id}",
                    headers={"Authorization": f"Bearer {self.bot.api_token}"}
                ) as response:
                    if response.status == 200:
                        settings = await response.json()
                        # キャッシュに保存（1時間有効）
                        self.settings_cache[guild_id] = settings
                        import time
                        self.cache_expire[guild_id] = time.time() + 3600
                        return settings
                    else:
                        logger.warning(f"Failed to get settings for guild {guild_id}: {response.status}")
                        return self._get_default_settings()
        except Exception as e:
            logger.error(f"Error getting guild settings: {e}")
            return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """デフォルトのレイド保護設定を返す"""
        return {
            "raidProtectionEnabled": False,
            "joinThreshold": 10,  # 10人以上
            "timeThreshold": 60,  # 60秒以内
            "actionType": "tempban",  # verify, kick, tempban, ban
            "logChannelId": None,
            "notifyRoleId": None
        }
    
    async def process_member_join(self, member: discord.Member) -> Tuple[bool, int]:
        """メンバー参加イベントを処理し、レイド検出を行う"""
        if not member.guild:
            return False, 0
        
        guild_id = str(member.guild.id)
        
        # ギルドの設定を取得
        settings = await self.get_guild_settings(guild_id)
        
        # レイド保護が無効なら無視
        if not settings.get("raidProtectionEnabled", False):
            return False, 0
        
        # 閾値を取得
        join_threshold = settings.get("joinThreshold", 10)
        time_threshold = settings.get("timeThreshold", 60)
        
        # 現在の時刻
        current_time = time.time()
        
        # 参加履歴に追加
        if guild_id not in self.join_history:
            self.join_history[guild_id] = deque()
        
        self.join_history[guild_id].append((member, current_time))
        
        # 古い参加履歴を削除
        cutoff_time = current_time - time_threshold
        while self.join_history[guild_id] and self.join_history[guild_id][0][1] < cutoff_time:
            self.join_history[guild_id].popleft()
        
        # 閾値内の参加者数をカウント
        recent_joins = len(self.join_history[guild_id])
        
        # アクティブなレイドがあるか確認
        is_raid_active = guild_id in self.active_raids
        
        # レイド検出条件を満たすか確認
        if recent_joins >= join_threshold:
            if not is_raid_active:
                # 新しいレイド検出
                self.active_raids[guild_id] = {
                    'start_time': current_time,
                    'count': recent_joins,
                    'members': {m.id for m, _ in self.join_history[guild_id]}
                }
                
                # レイド検出の通知
                await self._notify_raid_detected(member.guild, recent_joins)
            else:
                # 既存のレイド状態を更新
                self.active_raids[guild_id]['count'] += 1
                self.active_raids[guild_id]['members'].add(member.id)
            
            return True, recent_joins
        
        # アクティブなレイドがある場合、新しい参加者をレイドの一部として扱う
        if is_raid_active:
            self.active_raids[guild_id]['count'] += 1
            self.active_raids[guild_id]['members'].add(member.id)
            return True, self.active_raids[guild_id]['count']
        
        return False, recent_joins
    
    async def _notify_raid_detected(self, guild: discord.Guild, join_count: int):
        """レイド検出を通知する"""
        guild_id = str(guild.id)
        settings = await self.get_guild_settings(guild_id)
        
        log_channel_id = settings.get("logChannelId")
        notify_role_id = settings.get("notifyRoleId")
        
        if log_channel_id:
            try:
                log_channel = guild.get_channel(int(log_channel_id))
                if log_channel:
                    message = f"⚠️ **レイド検出** ⚠️\n{join_count}人のユーザーが短時間で参加しました！レイド警戒モードを有効化します。"
                    
                    # 通知ロールがある場合はメンション
                    if notify_role_id:
                        role = guild.get_role(int(notify_role_id))
                        if role:
                            message = f"{role.mention}\n{message}"
                    
                    await log_channel.send(message)
                    logger.warning(f"Raid detected in guild {guild.name} (ID: {guild.id}): {join_count} joins")
            except Exception as e:
                logger.error(f"Error sending raid notification: {e}")
    
    async def take_action(self, member: discord.Member) -> None:
        """レイド参加者と思われるメンバーに対してアクションを実行する"""
        if not member.guild:
            return
        
        guild_id = str(member.guild.id)
        settings = await self.get_guild_settings(guild_id)
        action_type = settings.get("actionType", "tempban")
        
        try:
            if action_type == "verify":
                # 認証ロールを剥奪（実装はサーバー固有の認証システムに依存）
                # 実装例: 認証前ロールを付与して、通常チャンネルへのアクセスを制限
                verify_role_id = settings.get("verifyRoleId")
                if verify_role_id:
                    verify_role = member.guild.get_role(int(verify_role_id))
                    if verify_role:
                        await member.add_roles(verify_role, reason="レイド保護: 自動認証要求")
                        logger.info(f"Applied verification role to {member} (ID: {member.id}) due to raid protection")
            
            elif action_type == "kick":
                # キック
                await member.kick(reason="レイド保護: 自動キック")
                logger.info(f"Kicked {member} (ID: {member.id}) due to raid protection")
            
            elif action_type == "tempban":
                # 一時的なBAN（7日間）
                await member.ban(reason="レイド保護: 自動一時BAN", delete_message_days=1)
                # 7日後にアンバンするためのタスクをスケジュール（実際の実装では永続化が必要）
                self.bot.loop.create_task(self._schedule_unban(member.guild.id, member.id, 7 * 24 * 60 * 60))
                logger.info(f"Temporarily banned {member} (ID: {member.id}) due to raid protection")
            
            elif action_type == "ban":
                # 永久BAN
                await member.ban(reason="レイド保護: 自動BAN", delete_message_days=1)
                logger.info(f"Banned {member} (ID: {member.id}) due to raid protection")
            
            # ログチャンネルに通知
            log_channel_id = settings.get("logChannelId")
            if log_channel_id:
                log_channel = member.guild.get_channel(int(log_channel_id))
                if log_channel:
                    action_text = {
                        "verify": "認証要求",
                        "kick": "キック",
                        "tempban": "一時BAN",
                        "ban": "BAN"
                    }.get(action_type, action_type)
                    
                    await log_channel.send(f"🛡️ レイド保護: {member.mention} ({member}) に対して {action_text} を適用しました。")
        except Exception as e:
            logger.error(f"Failed to apply {action_type} action: {e}")
    
    async def _schedule_unban(self, guild_id: int, user_id: int, delay: int):
        """指定した時間後にユーザーのBANを解除する"""
        await asyncio.sleep(delay)
        try:
            guild = self.bot.get_guild(guild_id)
            if guild:
                # BANリストからユーザーを取得
                ban_entry = None
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        ban_entry = entry
                        break
                
                if ban_entry:
                    await guild.unban(ban_entry.user, reason="レイド保護: 一時BANの期限切れ")
                    logger.info(f"Unbanned user ID {user_id} from guild {guild.name} (ID: {guild.id}) after temporary ban")
                    
                    # ログチャンネルに通知
                    settings = await self.get_guild_settings(str(guild_id))
                    log_channel_id = settings.get("logChannelId")
                    if log_channel_id:
                        log_channel = guild.get_channel(int(log_channel_id))
                        if log_channel:
                            await log_channel.send(f"🛡️ レイド保護: ユーザーID {user_id} の一時BANが期限切れになりました。BANを解除しました。")
        except Exception as e:
            logger.error(f"Failed to unban user {user_id}: {e}")
    
    def is_raid_active(self, guild_id: str) -> bool:
        """指定したギルドでレイドが検出されているかを返す"""
        return guild_id in self.active_raids
    
    def get_raid_info(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """現在のレイド情報を取得する"""
        if guild_id not in self.active_raids:
            return None
        
        raid_info = self.active_raids[guild_id].copy()
        raid_info['duration'] = time.time() - raid_info['start_time']
        return raid_info
    
    async def end_raid_mode(self, guild_id: str) -> bool:
        """レイド警戒モードを手動で終了する"""
        if guild_id not in self.active_raids:
            return False
        
        # レイド状態を削除
        del self.active_raids[guild_id]
        
        # サーバーにレイド終了を通知
        try:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                settings = await self.get_guild_settings(guild_id)
                log_channel_id = settings.get("logChannelId")
                if log_channel_id:
                    log_channel = guild.get_channel(int(log_channel_id))
                    if log_channel:
                        await log_channel.send("🛡️ レイド警戒モードを手動で解除しました。")
        except Exception as e:
            logger.error(f"Error sending raid end notification: {e}")
        
        return True
    
    async def invalidate_cache(self, guild_id: str) -> None:
        """ギルドのキャッシュを無効化する（設定変更時に呼び出す）"""
        self.settings_cache.pop(guild_id, None)
        self.cache_expire.pop(guild_id, None)
        logger.debug(f"Invalidated cache for guild {guild_id}") 