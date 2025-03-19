import discord
from discord.ext import commands
import asyncio
import logging
import time
from collections import defaultdict, deque
import aiohttp
from typing import Dict, List, Tuple, Set, Any, Optional

logger = logging.getLogger('ShardBot.AntiSpam')

class AntiSpam:
    """スパム対策機能を提供するクラス"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings_cache = {}  # guild_id: settings
        self.cache_expire = {}    # guild_id: timestamp
        
        # ユーザーごとのメッセージ履歴を保持
        self.user_message_history = defaultdict(lambda: defaultdict(deque))  # {guild_id: {user_id: deque(messages)}}
        self.user_mention_count = defaultdict(lambda: defaultdict(int))  # {guild_id: {user_id: count}}
        self.user_message_count = defaultdict(lambda: defaultdict(int))  # {guild_id: {user_id: count}}
        self.message_content_count = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # {guild_id: {user_id: {content_hash: count}}}
        
        # レート制限のリセットタイマー
        self.bot.loop.create_task(self._reset_counters_task())
        
        # 設定キャッシュの定期的なクリーンアップタスク
        self.bot.loop.create_task(self._cache_cleanup_task())
    
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
    
    async def _reset_counters_task(self):
        """レート制限カウンターをリセットするタスク"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # メッセージカウントとメンションカウントをリセット
                self.user_mention_count.clear()
                self.user_message_count.clear()
                self.message_content_count.clear()
                
                # 古いメッセージ履歴を削除
                for guild_id in self.user_message_history:
                    for user_id in list(self.user_message_history[guild_id].keys()):
                        # 最大で100件のメッセージ履歴を保持
                        while len(self.user_message_history[guild_id][user_id]) > 100:
                            self.user_message_history[guild_id][user_id].popleft()
            except Exception as e:
                logger.error(f"Error in reset counters task: {e}")
            
            await asyncio.sleep(10)  # 10秒ごとにリセット
    
    async def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """ギルドのスパム対策設定を取得する"""
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
        """デフォルトのスパム対策設定を返す"""
        return {
            "antiSpamEnabled": False,
            "duplicateThreshold": 3,
            "messageThreshold": 5,
            "mentionThreshold": 5,
            "actionType": "warn"  # warn, mute, kick, ban
        }
    
    def _content_hash(self, content: str) -> str:
        """メッセージ内容のハッシュ値を計算する（類似内容の検出用）"""
        # 単純化のために内容自体を使用（実際のアプリケーションではより効率的な方法を使用すべき）
        return content.strip().lower()
    
    def _update_message_history(self, guild_id: str, user_id: str, message: discord.Message):
        """ユーザーのメッセージ履歴を更新する"""
        # メッセージをキューに追加
        self.user_message_history[guild_id][user_id].append(message)
        
        # メッセージカウントを更新
        self.user_message_count[guild_id][user_id] += 1
        
        # メンションカウントを更新
        mention_count = len(message.mentions)
        if mention_count > 0:
            self.user_mention_count[guild_id][user_id] += mention_count
        
        # 重複コンテンツカウントを更新
        content_hash = self._content_hash(message.content)
        if content_hash:  # 空でない場合のみカウント
            self.message_content_count[guild_id][user_id][content_hash] += 1
    
    async def process_message(self, message: discord.Message) -> Tuple[bool, str, Dict[str, Any]]:
        """メッセージを処理し、スパムルールに違反しているかチェックする"""
        # DMは無視
        if not message.guild:
            return False, "", {}
        
        # ボットは無視
        if message.author.bot:
            return False, "", {}
        
        # 管理者は無視
        if message.author.guild_permissions.administrator:
            return False, "", {}
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # ギルドの設定を取得
        settings = await self.get_guild_settings(guild_id)
        
        # スパム対策が無効なら無視
        if not settings.get("antiSpamEnabled", False):
            return False, "", {}
        
        # メッセージ履歴を更新
        self._update_message_history(guild_id, user_id, message)
        
        # 閾値を取得
        duplicate_threshold = settings.get("duplicateThreshold", 3)
        message_threshold = settings.get("messageThreshold", 5)
        mention_threshold = settings.get("mentionThreshold", 5)
        
        # スパムチェック
        violation_reason = ""
        violation_data = {}
        
        # 1. 重複メッセージチェック
        content_hash = self._content_hash(message.content)
        if content_hash and self.message_content_count[guild_id][user_id][content_hash] >= duplicate_threshold:
            violation_reason = "duplicate_message"
            violation_data = {
                "content": message.content[:100] + ("..." if len(message.content) > 100 else ""),
                "count": self.message_content_count[guild_id][user_id][content_hash]
            }
            return True, violation_reason, violation_data
        
        # 2. メッセージ連投チェック
        if self.user_message_count[guild_id][user_id] >= message_threshold:
            violation_reason = "message_spam"
            violation_data = {
                "count": self.user_message_count[guild_id][user_id]
            }
            return True, violation_reason, violation_data
        
        # 3. メンション連投チェック
        if self.user_mention_count[guild_id][user_id] >= mention_threshold:
            violation_reason = "mention_spam"
            violation_data = {
                "count": self.user_mention_count[guild_id][user_id]
            }
            return True, violation_reason, violation_data
        
        return False, "", {}
    
    async def take_action(self, message: discord.Message, violation_type: str, violation_data: Dict[str, Any]) -> None:
        """違反に対してアクションを実行する"""
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        settings = await self.get_guild_settings(guild_id)
        action_type = settings.get("actionType", "warn")
        
        # 違反メッセージを削除
        try:
            await message.delete()
            logger.info(f"Deleted message from {message.author} (ID: {message.author.id}) due to {violation_type} violation")
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        
        # 違反タイプに応じたメッセージを作成
        warning_message = ""
        if violation_type == "duplicate_message":
            warning_message = f"{message.author.mention} 同じ内容のメッセージを{violation_data['count']}回送信したため、スパムと判断しました。"
        elif violation_type == "message_spam":
            warning_message = f"{message.author.mention} 短時間に{violation_data['count']}件のメッセージを送信したため、スパムと判断しました。"
        elif violation_type == "mention_spam":
            warning_message = f"{message.author.mention} 短時間に{violation_data['count']}人のメンションを行ったため、スパムと判断しました。"
        
        # アクションを実行
        try:
            if action_type == "warn":
                # 警告メッセージを送信
                await message.channel.send(warning_message, delete_after=10)
            
            elif action_type == "mute":
                # ミュート（タイムアウト）を適用
                await message.author.timeout(duration=300, reason=f"スパム検知: {violation_type}")
                await message.channel.send(f"{warning_message} 5分間のタイムアウトが適用されました。", delete_after=10)
            
            elif action_type == "kick":
                # キック
                await message.author.kick(reason=f"スパム検知: {violation_type}")
                await message.channel.send(f"{warning_message} サーバーからキックされました。", delete_after=10)
            
            elif action_type == "ban":
                # 一時的なBAN（1日）
                await message.author.ban(reason=f"スパム検知: {violation_type}", delete_message_days=1)
                await message.channel.send(f"{warning_message} サーバーからBANされました。", delete_after=10)
            
            logger.info(f"Applied {action_type} action to {message.author} (ID: {message.author.id}) for {violation_type}")
        except Exception as e:
            logger.error(f"Failed to apply {action_type} action: {e}")
    
    async def invalidate_cache(self, guild_id: str) -> None:
        """ギルドのキャッシュを無効化する（設定変更時に呼び出す）"""
        self.settings_cache.pop(guild_id, None)
        self.cache_expire.pop(guild_id, None)
        logger.debug(f"Invalidated cache for guild {guild_id}") 