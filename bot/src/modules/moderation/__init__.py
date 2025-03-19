from .automod import AutoModerator
from .antispam import AntiSpam
from .raid_protection import RaidProtection
from .captcha import CaptchaVerification
import logging
import discord
from typing import Dict, Any, Optional

logger = logging.getLogger('ShardBot.Moderation')

class ModerationManager:
    """すべてのモデレーション機能を管理するマネージャークラス"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # 各モデレーション機能を初期化
        self.auto_mod = AutoModerator(bot)
        self.anti_spam = AntiSpam(bot)
        self.raid_protection = RaidProtection(bot)
        self.captcha = CaptchaVerification(bot)
        
        logger.info("Moderation modules initialized")
    
    async def process_message(self, message: discord.Message) -> None:
        """メッセージを処理し、必要に応じてモデレーションアクションを実行する"""
        if not message.guild or message.author.bot:
            return
        
        # 1. 自動モデレーションによるフィルタリング
        auto_mod_result, violation_type, content = await self.auto_mod.process_message(message)
        if auto_mod_result:
            await self.auto_mod.take_action(message, violation_type, content)
            return  # 違反が見つかった場合は処理を終了
        
        # 2. スパム検出
        spam_result, spam_type, spam_data = await self.anti_spam.process_message(message)
        if spam_result:
            await self.anti_spam.take_action(message, spam_type, spam_data)
            return  # スパムが見つかった場合は処理を終了
        
        # 3. キャプチャ認証メッセージの処理
        await self.captcha.process_verification_message(message)
    
    async def process_member_join(self, member: discord.Member) -> None:
        """メンバー参加イベントを処理する"""
        if not member.guild:
            return
        
        # 1. レイド検出
        is_raid, join_count = await self.raid_protection.process_member_join(member)
        
        if is_raid:
            # レイド検出された場合、設定に応じたアクションを実行
            await self.raid_protection.take_action(member)
        
        # 2. キャプチャ認証の開始（レイド中でも実行する）
        await self.captcha.start_verification(member)
    
    async def invalidate_guild_cache(self, guild_id: str) -> None:
        """ギルドのキャッシュを無効化する（設定変更時に呼び出す）"""
        await self.auto_mod.invalidate_cache(guild_id)
        await self.anti_spam.invalidate_cache(guild_id)
        await self.raid_protection.invalidate_cache(guild_id)
        await self.captcha.invalidate_cache(guild_id)
        logger.debug(f"Invalidated all moderation caches for guild {guild_id}")
    
    async def end_raid_mode(self, guild_id: str) -> bool:
        """レイド警戒モードを手動で終了する"""
        return await self.raid_protection.end_raid_mode(guild_id)
    
    def is_raid_active(self, guild_id: str) -> bool:
        """指定したギルドでレイドが検出されているかを返す"""
        return self.raid_protection.is_raid_active(guild_id)
    
    def get_raid_info(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """現在のレイド情報を取得する"""
        return self.raid_protection.get_raid_info(guild_id)
