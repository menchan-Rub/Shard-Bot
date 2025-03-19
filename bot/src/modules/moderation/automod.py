import re
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
import json

logger = logging.getLogger('ShardBot.AutoMod')

class AutoModerator:
    """自動モデレーション機能を提供するクラス"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings_cache = {}  # guild_id: settings
        self.cache_expire = {}    # guild_id: timestamp
        self.default_bad_words = set()  # デフォルトの禁止ワードリスト
        self.invite_pattern = re.compile(r'discord(?:\.gg|app\.com\/invite|\.com\/invite)\/([a-zA-Z0-9\-]+)')
        self.url_pattern = re.compile(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
        
        # デフォルトの禁止ワードを読み込む
        self._load_default_bad_words()
        
        # 設定キャッシュの定期的なクリーンアップタスクを開始
        self.bot.loop.create_task(self._cache_cleanup_task())
    
    def _load_default_bad_words(self):
        """デフォルトの禁止ワードを読み込む"""
        try:
            with open('data/bad_words.txt', 'r', encoding='utf-8') as f:
                self.default_bad_words = {line.strip().lower() for line in f if line.strip()}
            logger.info(f"Loaded {len(self.default_bad_words)} default bad words")
        except FileNotFoundError:
            logger.warning("Default bad words file not found, creating empty list")
            self.default_bad_words = set()
            # ディレクトリが存在しない場合は作成
            import os
            os.makedirs('data', exist_ok=True)
            with open('data/bad_words.txt', 'w', encoding='utf-8') as f:
                f.write("# このファイルにはデフォルトの禁止ワードを1行ずつ記述します\n")
    
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
    
    async def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """ギルドの自動モデレーション設定を取得する"""
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
        """デフォルトの設定を返す"""
        return {
            "autoModEnabled": False,
            "filterBadWords": False,
            "customBadWords": "",
            "filterInvites": False,
            "filterLinks": False,
            "allowedLinks": "youtube.com,twitter.com,discord.com"
        }
    
    def _get_custom_bad_words(self, settings: Dict[str, Any]) -> Set[str]:
        """カスタム禁止ワードのセットを取得する"""
        custom_words_str = settings.get("customBadWords", "")
        if not custom_words_str:
            return set()
        
        # カンマまたは改行で区切られたワードをセットに変換
        words = set()
        for word in re.split(r'[,\n]', custom_words_str):
            word = word.strip().lower()
            if word:
                words.add(word)
        
        return words
    
    def _get_allowed_links(self, settings: Dict[str, Any]) -> Set[str]:
        """許可されたリンクのセットを取得する"""
        allowed_links_str = settings.get("allowedLinks", "")
        if not allowed_links_str:
            return set()
        
        # カンマで区切られたドメインをセットに変換
        domains = set()
        for domain in allowed_links_str.split(','):
            domain = domain.strip().lower()
            if domain:
                domains.add(domain)
        
        return domains
    
    def _check_contains_bad_word(self, content: str, bad_words: Set[str]) -> Optional[str]:
        """メッセージに禁止ワードが含まれているかチェックする"""
        content_lower = content.lower()
        
        for word in bad_words:
            # 単語の境界をチェック
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content_lower):
                return word
        
        return None
    
    def _check_contains_invite(self, content: str) -> Optional[str]:
        """メッセージにDiscord招待リンクが含まれているかチェックする"""
        match = self.invite_pattern.search(content)
        if match:
            return match.group(0)
        return None
    
    def _check_contains_url(self, content: str, allowed_domains: Set[str]) -> Optional[str]:
        """メッセージに禁止URLが含まれているかチェックする"""
        for match in self.url_pattern.finditer(content):
            url = match.group(0)
            
            # 許可されたドメインかチェック
            is_allowed = False
            for domain in allowed_domains:
                if domain in url:
                    is_allowed = True
                    break
            
            if not is_allowed:
                return url
        
        return None
    
    async def process_message(self, message: discord.Message) -> Tuple[bool, str, str]:
        """メッセージを処理し、フィルタールールに違反しているかチェックする"""
        # DMは無視
        if not message.guild:
            return False, "", ""
        
        # ボットは無視
        if message.author.bot:
            return False, "", ""
        
        # 管理者は無視
        if message.author.guild_permissions.administrator:
            return False, "", ""
        
        # ギルドの設定を取得
        settings = await self.get_guild_settings(str(message.guild.id))
        
        # 自動モデレーションが無効なら無視
        if not settings.get("autoModEnabled", False):
            return False, "", ""
        
        # 禁止ワードチェック
        if settings.get("filterBadWords", False):
            # デフォルトの禁止ワードとカスタム禁止ワードを組み合わせる
            bad_words = self.default_bad_words.union(self._get_custom_bad_words(settings))
            
            bad_word = self._check_contains_bad_word(message.content, bad_words)
            if bad_word:
                return True, "bad_word", bad_word
        
        # 招待リンクチェック
        if settings.get("filterInvites", False):
            invite = self._check_contains_invite(message.content)
            if invite:
                return True, "invite", invite
        
        # URLチェック
        if settings.get("filterLinks", False):
            allowed_domains = self._get_allowed_links(settings)
            url = self._check_contains_url(message.content, allowed_domains)
            if url:
                return True, "url", url
        
        return False, "", ""
    
    async def take_action(self, message: discord.Message, violation_type: str, content: str) -> None:
        """違反に対してアクションを実行する"""
        # メッセージを削除
        try:
            await message.delete()
            logger.info(f"Deleted message from {message.author} (ID: {message.author.id}) due to {violation_type} violation: {content}")
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        
        # 違反タイプに応じて警告を送信
        try:
            if violation_type == "bad_word":
                await message.channel.send(
                    f"{message.author.mention} 禁止ワードが含まれているため、メッセージを削除しました。",
                    delete_after=5
                )
            elif violation_type == "invite":
                await message.channel.send(
                    f"{message.author.mention} 招待リンクが含まれているため、メッセージを削除しました。",
                    delete_after=5
                )
            elif violation_type == "url":
                await message.channel.send(
                    f"{message.author.mention} 許可されていないURLが含まれているため、メッセージを削除しました。",
                    delete_after=5
                )
        except Exception as e:
            logger.error(f"Failed to send warning message: {e}")

    async def invalidate_cache(self, guild_id: str) -> None:
        """ギルドのキャッシュを無効化する（設定変更時に呼び出す）"""
        self.settings_cache.pop(guild_id, None)
        self.cache_expire.pop(guild_id, None)
        logger.debug(f"Invalidated cache for guild {guild_id}") 