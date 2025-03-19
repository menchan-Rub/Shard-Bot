import discord
from discord.ext import commands
import asyncio
import logging
import random
import string
import io
import aiohttp
from typing import Dict, List, Set, Any, Optional, Tuple
import time
import datetime
from PIL import Image, ImageDraw, ImageFont
import os

logger = logging.getLogger('ShardBot.Captcha')

class CaptchaVerification:
    """キャプチャ認証機能を提供するクラス"""
    
    def __init__(self, bot):
        self.bot = bot
        self.settings_cache = {}  # guild_id: settings
        self.cache_expire = {}    # guild_id: timestamp
        
        # キャプチャコード保存用
        self.pending_verifications = {}  # {guild_id: {user_id: {"code": "...", "expires": timestamp, "attempts": 0}}}
        
        # キャプチャ関連ファイルのパス
        self.fonts_path = "data/fonts"
        self.default_font = "NotoSansJP-Regular.ttf"
        
        # フォントが存在しない場合は初期化時にダウンロード
        self.bot.loop.create_task(self._ensure_fonts_exist())
        
        # 設定キャッシュの定期的なクリーンアップタスク
        self.bot.loop.create_task(self._cache_cleanup_task())
        
        # 期限切れの認証を定期的にクリーンアップするタスク
        self.bot.loop.create_task(self._verification_cleanup_task())
    
    async def _ensure_fonts_exist(self):
        """必要なフォントが存在することを確認し、存在しない場合はダウンロード"""
        await self.bot.wait_until_ready()
        
        try:
            os.makedirs(self.fonts_path, exist_ok=True)
            
            font_path = os.path.join(self.fonts_path, self.default_font)
            if not os.path.exists(font_path):
                # Noto Sans JPをダウンロード
                logger.info(f"Downloading font {self.default_font}...")
                
                # フォントをダウンロード（例としてGoogle Fontsから）
                font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf"
                async with aiohttp.ClientSession() as session:
                    async with session.get(font_url) as response:
                        if response.status == 200:
                            with open(font_path, "wb") as f:
                                f.write(await response.read())
                            logger.info(f"Font {self.default_font} downloaded successfully")
                        else:
                            logger.error(f"Failed to download font: {response.status}")
                            # 代替フォントとしてDejaVu Sansを使用
                            self.default_font = None
            
            # フォントが利用可能かテスト
            try:
                if os.path.exists(font_path):
                    ImageFont.truetype(font_path, 24)
                    logger.info(f"Font {self.default_font} loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load font: {e}")
                self.default_font = None
        
        except Exception as e:
            logger.error(f"Error ensuring fonts exist: {e}")
            self.default_font = None
    
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
    
    async def _verification_cleanup_task(self):
        """期限切れの認証試行を定期的にクリーンアップする"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                current_time = time.time()
                
                for guild_id in list(self.pending_verifications.keys()):
                    for user_id in list(self.pending_verifications[guild_id].keys()):
                        if current_time > self.pending_verifications[guild_id][user_id]["expires"]:
                            # 期限切れのユーザーをキック（設定が有効な場合）
                            settings = await self.get_guild_settings(guild_id)
                            
                            if settings.get("captchaEnabled", False) and settings.get("kickOnFailure", False):
                                try:
                                    guild = self.bot.get_guild(int(guild_id))
                                    if guild:
                                        member = guild.get_member(int(user_id))
                                        if member:
                                            await member.kick(reason="キャプチャ認証の時間切れ")
                                            logger.info(f"Kicked {member} (ID: {member.id}) due to captcha timeout")
                                            
                                            # ログチャンネルに通知
                                            log_channel_id = settings.get("logChannelId")
                                            if log_channel_id:
                                                log_channel = guild.get_channel(int(log_channel_id))
                                                if log_channel:
                                                    await log_channel.send(f"🔒 {member.mention} (ID: {member.id}) はキャプチャ認証の時間切れでキックされました。")
                                except Exception as e:
                                    logger.error(f"Failed to kick user for captcha timeout: {e}")
                            
                            # 期限切れエントリを削除
                            del self.pending_verifications[guild_id][user_id]
                            
                    # ギルドの認証リストが空になった場合は削除
                    if not self.pending_verifications[guild_id]:
                        del self.pending_verifications[guild_id]
            
            except Exception as e:
                logger.error(f"Error in verification cleanup task: {e}")
            
            await asyncio.sleep(60)  # 1分ごとに実行
    
    async def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """ギルドのキャプチャ認証設定を取得する"""
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
        """デフォルトのキャプチャ認証設定を返す"""
        return {
            "captchaEnabled": False,
            "captchaType": "text",  # text, math
            "captchaLength": 6,
            "verificationTimeout": 300,  # 5分のタイムアウト
            "maxAttempts": 3,
            "kickOnFailure": True,
            "captchaChannelId": None,
            "successRoleId": None,
            "logChannelId": None
        }
    
    def _generate_captcha_code(self, captcha_type: str, length: int = 6) -> Tuple[str, str]:
        """キャプチャコードを生成する"""
        if captcha_type == "math":
            # 簡単な数学の問題を生成
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            op = random.choice(["+", "-", "*"])
            
            question = f"{a} {op} {b} = ?"
            
            if op == "+":
                answer = str(a + b)
            elif op == "-":
                answer = str(a - b)
            else:  # op == "*"
                answer = str(a * b)
            
            return question, answer
        
        else:  # captcha_type == "text"
            # ランダムな文字列を生成
            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choice(chars) for _ in range(length))
            return code, code
    
    def _generate_captcha_image(self, text: str) -> discord.File:
        """キャプチャ画像を生成する"""
        width, height = 280, 120
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # フォントの読み込み
        font_path = os.path.join(self.fonts_path, self.default_font) if self.default_font else None
        try:
            font = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
        except Exception as e:
            logger.error(f"Failed to load font: {e}")
            font = ImageFont.load_default()
        
        # ノイズを追加（線）
        for _ in range(8):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(64, 64, 64), width=1)
        
        # ノイズを追加（点）
        for _ in range(800):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(64, 64, 64))
        
        # テキストを描画
        text_width, text_height = draw.textsize(text, font=font)
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), text, font=font, fill=(0, 0, 0))
        
        # 画像をバイトストリームに変換
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        return discord.File(buffer, filename="captcha.png")
    
    async def start_verification(self, member: discord.Member) -> None:
        """新しいメンバーに対してキャプチャ認証を開始する"""
        if not member.guild:
            return
        
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        # ギルドの設定を取得
        settings = await self.get_guild_settings(guild_id)
        
        # キャプチャが無効なら無視
        if not settings.get("captchaEnabled", False):
            return
        
        # キャプチャチャンネルを取得
        captcha_channel_id = settings.get("captchaChannelId")
        if not captcha_channel_id:
            logger.warning(f"Captcha channel not set for guild {guild_id}")
            return
        
        try:
            captcha_channel = member.guild.get_channel(int(captcha_channel_id))
            if not captcha_channel:
                logger.warning(f"Captcha channel {captcha_channel_id} not found in guild {guild_id}")
                return
            
            # キャプチャタイプと長さを取得
            captcha_type = settings.get("captchaType", "text")
            captcha_length = settings.get("captchaLength", 6)
            
            # キャプチャコードを生成
            question, answer = self._generate_captcha_code(captcha_type, captcha_length)
            
            # 期限を設定
            timeout = settings.get("verificationTimeout", 300)
            expires = time.time() + timeout
            
            # 認証情報を保存
            if guild_id not in self.pending_verifications:
                self.pending_verifications[guild_id] = {}
                
            self.pending_verifications[guild_id][user_id] = {
                "code": answer,
                "expires": expires,
                "attempts": 0
            }
            
            # キャプチャ画像を生成
            captcha_file = self._generate_captcha_image(question)
            
            # 認証メッセージを送信
            timeout_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=timeout)
            await captcha_channel.send(
                f"{member.mention} このサーバーにアクセスするには、下の画像に表示されている文字を入力してください。"
                f"\n⏱️ 制限時間: <t:{int(expires)}:R>"
                f"\n❗ 最大試行回数: {settings.get('maxAttempts', 3)}回",
                file=captcha_file
            )
            
            logger.info(f"Started captcha verification for {member} (ID: {member.id}) in guild {member.guild.name}")
        
        except Exception as e:
            logger.error(f"Error starting captcha verification: {e}")
    
    async def process_verification_message(self, message: discord.Message) -> None:
        """キャプチャ認証メッセージを処理する"""
        if not message.guild or message.author.bot:
            return
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # ギルドの設定を取得
        settings = await self.get_guild_settings(guild_id)
        
        # キャプチャが無効なら無視
        if not settings.get("captchaEnabled", False):
            return
        
        # キャプチャチャンネルでない場合は無視
        captcha_channel_id = settings.get("captchaChannelId")
        if not captcha_channel_id or str(message.channel.id) != captcha_channel_id:
            return
        
        # ユーザーがキャプチャ認証待ちでない場合は無視
        if guild_id not in self.pending_verifications or user_id not in self.pending_verifications[guild_id]:
            return
        
        verification = self.pending_verifications[guild_id][user_id]
        
        # 試行回数を増やす
        verification["attempts"] += 1
        max_attempts = settings.get("maxAttempts", 3)
        
        # キャプチャコードが一致するか確認
        if message.content.strip().lower() == verification["code"].lower():
            # 認証成功
            try:
                # 成功メッセージを送信
                await message.channel.send(
                    f"{message.author.mention} ✅ 認証に成功しました！サーバーにアクセスできるようになりました。",
                    delete_after=10
                )
                
                # 認証ロールを付与
                success_role_id = settings.get("successRoleId")
                if success_role_id:
                    success_role = message.guild.get_role(int(success_role_id))
                    if success_role:
                        await message.author.add_roles(success_role, reason="キャプチャ認証成功")
                
                # ログチャンネルに通知
                log_channel_id = settings.get("logChannelId")
                if log_channel_id:
                    log_channel = message.guild.get_channel(int(log_channel_id))
                    if log_channel:
                        await log_channel.send(f"🔓 {message.author.mention} (ID: {message.author.id}) がキャプチャ認証に成功しました。")
                
                # 認証情報を削除
                del self.pending_verifications[guild_id][user_id]
                if not self.pending_verifications[guild_id]:
                    del self.pending_verifications[guild_id]
                
                logger.info(f"Captcha verification successful for {message.author} (ID: {message.author.id}) in guild {message.guild.name}")
            
            except Exception as e:
                logger.error(f"Error processing successful verification: {e}")
        
        else:
            # 認証失敗
            try:
                if verification["attempts"] >= max_attempts:
                    # 最大試行回数に達した場合
                    await message.channel.send(
                        f"{message.author.mention} ❌ 認証に失敗しました。最大試行回数に達したため、サーバーからキックされます。",
                        delete_after=10
                    )
                    
                    # ユーザーをキック
                    if settings.get("kickOnFailure", True):
                        await message.author.kick(reason="キャプチャ認証の失敗")
                        
                        # ログチャンネルに通知
                        log_channel_id = settings.get("logChannelId")
                        if log_channel_id:
                            log_channel = message.guild.get_channel(int(log_channel_id))
                            if log_channel:
                                await log_channel.send(f"🔒 {message.author.mention} (ID: {message.author.id}) はキャプチャ認証の失敗でキックされました。")
                    
                    # 認証情報を削除
                    del self.pending_verifications[guild_id][user_id]
                    if not self.pending_verifications[guild_id]:
                        del self.pending_verifications[guild_id]
                    
                    logger.info(f"Captcha verification failed (max attempts) for {message.author} (ID: {message.author.id}) in guild {message.guild.name}")
                
                else:
                    # まだ試行回数が残っている場合
                    remaining = max_attempts - verification["attempts"]
                    await message.channel.send(
                        f"{message.author.mention} ❌ 認証に失敗しました。あと{remaining}回試行できます。",
                        delete_after=10
                    )
                    
                    logger.info(f"Captcha verification attempt failed for {message.author} (ID: {message.author.id}), {remaining} attempts remaining")
            
            except Exception as e:
                logger.error(f"Error processing failed verification: {e}")
    
    async def invalidate_cache(self, guild_id: str) -> None:
        """ギルドのキャッシュを無効化する（設定変更時に呼び出す）"""
        self.settings_cache.pop(guild_id, None)
        self.cache_expire.pop(guild_id, None)
        logger.debug(f"Invalidated cache for guild {guild_id}") 