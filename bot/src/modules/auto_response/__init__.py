import logging
import os
import re
import random
import asyncio
import json
import aiohttp
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Deque
from collections import defaultdict, deque

import discord
from discord.ext import commands

from bot.src.db.database import get_auto_response_settings, get_db_session
from bot.src.db.repository import AutoResponseSettingsRepository
from bot.src.db.models import AutoResponseSettings

__all__ = ['AutoResponse']

class AutoResponse:
    """自動応答システム"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('modules.auto_response')
        
        # デフォルト設定
        self.enabled = False
        self.response_chance = 0.1
        self.cooldown = 60
        self.max_context_length = 10
        self.ignore_bots = True
        self.ignore_prefixes = ['!', '?', '/', '.', '-']
        self.ai_enabled = False
        self.temperature = 0.7
        self.ai_persona = 'あなたはフレンドリーで役立つアシスタントです。'
        self.custom_responses = {}
        
        # 設定と状態の保持
        self.settings = {}  # Guild ID -> Settings
        self.message_context = {}  # Guild ID -> Channel ID -> 最近のメッセージリスト
        self.cooldowns = {}  # Guild ID -> Channel ID -> 最後の応答時刻
        self.response_stats = {}  # Guild ID -> 統計情報
        
        # コンテキスト履歴（チャンネルごと）
        self.message_history = defaultdict(lambda: deque(maxlen=self.max_context_length))
        
        # AI APIキー
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-1.0-pro')
        
        # AIが有効かどうか
        self.ai_available = self.api_key is not None
        
        # API Session
        self.session = None
        self.model = None
        
        self.logger.info('自動応答システム初期化中...')
        
        # バックグラウンドタスク
        self.bot.loop.create_task(self._initialize())
        
    async def _initialize(self):
        """初期化処理"""
        await self.bot.wait_until_ready()
        self.session = aiohttp.ClientSession()
        await self.setup()
        
        # Gemini APIの設定
        if self.api_key and self.ai_enabled:
            await self._setup_gemini_api()
        
        # 定期的に設定を再読み込み（1時間ごと）
        self.bot.loop.create_task(self._periodic_reload_settings())
        
    async def setup(self):
        """初期設定"""
        # 全サーバーの設定を読み込む
        self.logger.info('全サーバーの自動応答設定を読み込みます')
        
        for guild in self.bot.guilds:
            await self.load_guild_settings(str(guild.id))
            
        self.logger.info('自動応答システム初期化完了')
        
    async def load_guild_settings(self, guild_id: str) -> None:
        """
        特定のギルドの設定を読み込む
        """
        try:
            db_settings = await get_auto_response_settings(guild_id)
            
            if db_settings:
                # 基本設定
                self.enabled = db_settings.enabled
                self.response_chance = db_settings.response_chance
                self.cooldown = db_settings.cooldown
                self.max_context_length = db_settings.max_context_length
                
                # AI設定
                self.ai_enabled = db_settings.ai_enabled
                self.temperature = db_settings.ai_temperature
                self.ai_persona = db_settings.ai_persona
                
                # 除外設定
                self.ignore_bots = db_settings.ignore_bots
                self.ignore_prefixes = db_settings.ignore_prefixes
                
                # カスタム応答パターン
                if db_settings.custom_responses:
                    self.custom_responses = db_settings.custom_responses
                    
                # コンテキスト履歴の最大長を更新
                for key in self.message_history:
                    self.message_history[key] = deque(list(self.message_history[key]), maxlen=self.max_context_length)
                
                # Gemini APIの再設定（温度が変更された場合など）
                if self.ai_enabled and self.api_key and self.model:
                    self.model.generation_config["temperature"] = self.temperature
                
                self.settings[guild_id] = db_settings
                self.logger.debug(f"ギルド {guild_id} の自動応答設定を読み込みました")
                return True
            else:
                self.logger.warning(f"ギルド {guild_id} の自動応答設定が見つかりませんでした")
                # デフォルト設定を使用
                default_settings = AutoResponseSettings(
                    guild_id=guild_id,
                    enabled=False,
                    response_chance=0.1,
                    cooldown=60,
                    max_context_length=10,
                    ignore_bots=True,
                    ignore_prefixes=['!', '?', '/', '.', '-'],
                    ai_enabled=False,
                    ai_temperature=0.7,
                    ai_persona='あなたはフレンドリーで役立つアシスタントです。',
                    custom_responses={}
                )
                self.settings[guild_id] = default_settings
                return False
                
        except Exception as e:
            self.logger.error(f"設定読み込み中にエラーが発生: {e}")
            # デフォルト設定を使用
            default_settings = AutoResponseSettings(
                guild_id=guild_id,
                enabled=False,
                response_chance=0.1,
                cooldown=60,
                max_context_length=10,
                ignore_bots=True,
                ignore_prefixes=['!', '?', '/', '.', '-'],
                ai_enabled=False,
                ai_temperature=0.7,
                ai_persona='あなたはフレンドリーで役立つアシスタントです。',
                custom_responses={}
            )
            self.settings[guild_id] = default_settings
            return False
    
    async def _setup_gemini_api(self):
        """Gemini APIのセットアップ"""
        try:
            genai.configure(api_key=self.api_key)
            # モデルのロード
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 200,
                },
            )
            self.logger.info(f"Gemini AI 自動応答システムが初期化されました: {self.model_name}")
        except Exception as e:
            self.model = None
            self.logger.error(f"Gemini API初期化中にエラーが発生: {e}")
    
    async def close(self):
        """終了処理"""
        if self.session:
            await self.session.close()
    
    async def should_respond(self, message: discord.Message) -> bool:
        """自動応答すべきかどうか判断"""
        if not message.guild:
            return False
            
        guild_id = str(message.guild.id)
        
        # このギルドの設定を取得
        if guild_id not in self.settings:
            await self.load_guild_settings(guild_id)
        
        settings = self.settings.get(guild_id)
        if not settings or not settings.enabled:
            return False
        
        # ボットメッセージは除外
        if message.author.bot and settings.ignore_bots:
            return False
            
        # 無視するプレフィックスをチェック
        for prefix in settings.ignore_prefixes:
            if message.content.startswith(prefix):
                return False
                
        # クールダウンをチェック
        cooldown_key = f"{guild_id}:{message.channel.id}"
        cooldown_time = settings.cooldown
        
        if cooldown_key in self.cooldowns:
            if datetime.utcnow() - self.cooldowns[cooldown_key] < timedelta(seconds=cooldown_time):
                return False
                
        # 応答確率でチェック
        if random.random() > settings.response_chance:
            return False
            
        return True
        
    async def get_response(self, message: discord.Message) -> Optional[str]:
        """メッセージに対する応答を生成"""
        if not message.guild:
            return None
            
        guild_id = str(message.guild.id)
        settings = self.settings.get(guild_id)
        if not settings:
            return None
            
        content = message.content.lower()
        
        # コンテキスト履歴を更新
        context_key = f"{guild_id}:{message.channel.id}"
        if context_key not in self.message_history:
            self.message_history[context_key] = deque(maxlen=settings.max_context_length)
            
        self.message_history[context_key].append({
            'author_id': message.author.id,
            'author_name': str(message.author),
            'content': message.content,
            'timestamp': message.created_at.isoformat()
        })
        
        # カスタム応答パターン
        custom_response = self._check_custom_patterns(content, settings.custom_responses)
        if custom_response:
            return custom_response
                
        # AIパワード応答が有効な場合
        if settings.ai_enabled and self.model and self.api_key:
            return await self._generate_ai_response(message, settings)
            
        # 一般的な応答パターン
        general_responses = [
            "なるほど、興味深いですね。",
            "それは素晴らしいですね！",
            "もう少し詳しく教えていただけますか？",
            "それについて、他の方はどう思いますか？",
            "確かにそうですね。",
            "なるほど、そのような考え方もありますね。",
            "それは面白い視点ですね。",
            "その通りですね！",
            "それは素敵な考えですね。",
            "ありがとうございます、参考になります。"
        ]
        
        return random.choice(general_responses)
        
    def _check_custom_patterns(self, content: str, custom_responses: Dict[str, List[str]]) -> Optional[str]:
        """カスタムパターンにマッチするか確認"""
        if not custom_responses:
            return None
            
        for pattern, responses in custom_responses.items():
            if re.search(pattern, content, re.IGNORECASE):
                return random.choice(responses)
        return None
        
    async def _generate_ai_response(self, message: discord.Message, settings) -> Optional[str]:
        """Gemini APIを使って応答を生成"""
        if not self.model:
            return None
            
        # コンテキストの取得
        guild_id = str(message.guild.id)
        channel_id = message.channel.id
        context_key = f"{guild_id}:{channel_id}"
        
        context = list(self.message_history.get(context_key, []))
        
        # プロンプトの構築
        prompt = f"{settings.ai_persona}\n\n"
        prompt += "以下は最近のメッセージです:\n\n"
        
        for msg in context[-5:]:  # 最新5件のみ使用
            prompt += f"ユーザー {msg['author_name']}: {msg['content']}\n"
        
        prompt += f"\nユーザー {message.author}: {message.content}\n"
        prompt += "\nあなた: "
        
        try:
            # モデルに問い合わせ
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # 応答テキストの抽出と整形
            if response.text:
                # 150文字までの応答に制限
                result = response.text.strip()
                if len(result) > 150:
                    result = result[:147] + "..."
                return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Gemini API呼び出し中にエラーが発生: {e}")
            return None
        
    async def process_message(self, message: discord.Message) -> None:
        """メッセージを処理して応答"""
        if not message.guild:
            return
            
        # 応答すべきか判断
        if not await self.should_respond(message):
            return
            
        guild_id = str(message.guild.id)
        
        # コンテキストを更新
        self._update_context(message)
        
        # 応答生成
        response_text = await self.get_response(message)
        if not response_text:
            return
            
        # 応答を送信
        try:
            await message.channel.send(response_text)
            
            # 統計を更新
            self._update_stats(guild_id, message.channel.id, message.author.id)
            
            # 最後の応答時間を記録
            cooldown_key = f"{guild_id}:{message.channel.id}"
            self.cooldowns[cooldown_key] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"応答の送信中にエラーが発生: {e}")
    
    def _update_context(self, message: discord.Message) -> None:
        """チャンネルのコンテキストを更新"""
        if not message.guild:
            return
            
        guild_id = str(message.guild.id)
        channel_id = message.channel.id
        
        # コンテキストキー
        context_key = f"{guild_id}:{channel_id}"
        
        # このギルド・チャンネルのコンテキストを取得または初期化
        if guild_id not in self.message_context:
            self.message_context[guild_id] = {}
            
        if channel_id not in self.message_context[guild_id]:
            self.message_context[guild_id][channel_id] = []
        
        # 新しいメッセージを追加
        context = self.message_context[guild_id][channel_id]
        context.append({
            'author': str(message.author),
            'author_id': message.author.id,
            'content': message.content,
            'timestamp': message.created_at.isoformat()
        })
        
        # 設定から最大長さを取得
        settings = self.settings.get(guild_id)
        max_length = 10  # デフォルト値
        if settings and hasattr(settings, 'max_context_length'):
            max_length = settings.max_context_length
        
        # 最大長さを制限
        if len(context) > max_length:
            self.message_context[guild_id][channel_id] = context[-max_length:]
    
    def _update_stats(self, guild_id: str, channel_id: int, user_id: int) -> None:
        """応答統計を更新"""
        # ギルド統計
        if guild_id not in self.response_stats:
            self.response_stats[guild_id] = {
                'total_responses': 0,
                'channels': {},
                'users': {},
                'hour_distribution': [0] * 24,
                'weekday_distribution': [0] * 7,
            }
        
        guild_stats = self.response_stats[guild_id]
        guild_stats['total_responses'] += 1
        
        # チャンネル統計
        if channel_id not in guild_stats['channels']:
            guild_stats['channels'][channel_id] = 0
        guild_stats['channels'][channel_id] += 1
        
        # ユーザー統計
        if user_id not in guild_stats['users']:
            guild_stats['users'][user_id] = 0
        guild_stats['users'][user_id] += 1
        
        # 時間帯分布
        current_time = datetime.utcnow()
        hour = current_time.hour
        weekday = current_time.weekday()
        
        guild_stats['hour_distribution'][hour] += 1
        guild_stats['weekday_distribution'][weekday] += 1
    
    def get_channel_stats(self, guild_id: str, channel_id: int) -> Dict[str, Any]:
        """チャンネルの応答統計を取得"""
        if guild_id not in self.response_stats:
            return {'total_responses': 0}
            
        guild_stats = self.response_stats[guild_id]
        channel_responses = guild_stats['channels'].get(channel_id, 0)
        
        return {
            'total_responses': channel_responses,
            'guild_total': guild_stats['total_responses'],
            'percentage': (channel_responses / guild_stats['total_responses'] * 100) if guild_stats['total_responses'] > 0 else 0
        }
    
    def get_guild_stats(self, guild_id: str) -> Dict[str, Any]:
        """ギルドの応答統計を取得"""
        if guild_id not in self.response_stats:
            return {
                'total_responses': 0,
                'top_channels': [],
                'top_users': [],
                'hour_distribution': [0] * 24,
                'weekday_distribution': [0] * 7
            }
            
        guild_stats = self.response_stats[guild_id]
        
        # トップチャンネルを取得
        top_channels = sorted(
            guild_stats['channels'].items(),
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # トップユーザーを取得
        top_users = sorted(
            guild_stats['users'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_responses': guild_stats['total_responses'],
            'top_channels': top_channels,
            'top_users': top_users,
            'hour_distribution': guild_stats['hour_distribution'],
            'weekday_distribution': guild_stats['weekday_distribution']
        }
        
    async def generate_report(self, guild, days: int = 30) -> Optional[discord.Embed]:
        """
        自動応答システムのレポートを生成
        
        Args:
            guild: 対象のギルド
            days: レポート期間（日数）
            
        Returns:
            discord.Embed: レポート用Embedオブジェクト
        """
        if not guild:
            return None
            
        guild_id = str(guild.id)
        stats = self.get_guild_stats(guild_id)
        
        if stats['total_responses'] == 0:
            return discord.Embed(
                title="🤖 自動応答システムレポート",
                description="記録されたデータがありません。",
                color=discord.Color.blue()
            )
        
        embed = discord.Embed(
            title="🤖 自動応答システムレポート",
            description=f"期間: 過去{days}日間",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="総応答数",
            value=f"{stats['total_responses']}回",
            inline=True
        )
        
        # トップチャンネル
        if stats['top_channels']:
            top_channels_text = ""
            for channel_id, count in stats['top_channels']:
                channel = guild.get_channel(channel_id)
                channel_name = f"#{channel.name}" if channel else f"不明なチャンネル({channel_id})"
                percentage = (count / stats['total_responses']) * 100
                top_channels_text += f"{channel_name}: {count}回 ({percentage:.1f}%)\n"
                
            embed.add_field(
                name="応答数トップチャンネル",
                value=top_channels_text,
                inline=False
            )
        
        # トップユーザー
        if stats['top_users']:
            top_users_text = ""
            for user_id, count in stats['top_users']:
                user = guild.get_member(user_id)
                user_name = str(user) if user else f"不明なユーザー({user_id})"
                percentage = (count / stats['total_responses']) * 100
                top_users_text += f"{user_name}: {count}回 ({percentage:.1f}%)\n"
                
            embed.add_field(
                name="応答数トップユーザー",
                value=top_users_text,
                inline=False
            )
        
        # 時間帯分布
        hour_data = stats['hour_distribution']
        max_hour_count = max(hour_data) if hour_data else 0
        
        if max_hour_count > 0:
            hour_text = ""
            peak_hours = []
            
            for hour, count in enumerate(hour_data):
                if count == max_hour_count:
                    peak_hours.append(f"{hour}時")
            
            hour_text += f"ピーク時間帯: {', '.join(peak_hours)}\n\n"
            
            for i in range(0, 24, 6):
                segment = hour_data[i:i+6]
                hour_text += f"{i}時-{i+5}時: {sum(segment)}回\n"
            
            embed.add_field(
                name="時間帯別応答分布",
                value=hour_text,
                inline=False
            )
        
        # 曜日分布
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        weekday_data = stats['weekday_distribution']
        max_weekday_count = max(weekday_data) if weekday_data else 0
        
        if max_weekday_count > 0:
            weekday_text = ""
            
            for weekday, count in enumerate(weekday_data):
                percentage = (count / sum(weekday_data)) * 100
                weekday_text += f"{weekday_names[weekday]}曜日: {count}回 ({percentage:.1f}%)\n"
            
            embed.add_field(
                name="曜日別応答分布",
                value=weekday_text,
                inline=False
            )
        
        return embed
    
    async def update_settings(self, guild_id: str, settings) -> bool:
        """
        サーバーごとの設定を更新
        
        Args:
            guild_id: ギルドID
            settings: 設定オブジェクト
            
        Returns:
            bool: 更新が成功したかどうか
        """
        try:
            # メモリ内の設定を更新
            settings_updated = False
            
            # 現在の設定を取得
            current_settings = self.settings.get(guild_id)
            if not current_settings:
                # 設定がなければデフォルト値で初期化
                current_settings = AutoResponseSettings(
                    guild_id=guild_id,
                    enabled=False,
                    response_chance=0.1,
                    cooldown=60,
                    max_context_length=10,
                    ignore_bots=True,
                    ignore_prefixes=['!', '?', '/', '.', '-'],
                    ai_enabled=False,
                    ai_temperature=0.7,
                    ai_persona='あなたはフレンドリーで役立つアシスタントです。',
                    custom_responses={}
                )
                self.settings[guild_id] = current_settings
            
            # 基本設定
            if hasattr(settings, 'enabled') and settings.enabled is not None:
                current_settings.enabled = settings.enabled
                settings_updated = True
                
            if hasattr(settings, 'response_chance') and settings.response_chance is not None:
                current_settings.response_chance = float(settings.response_chance)
                settings_updated = True
                
            if hasattr(settings, 'cooldown') and settings.cooldown is not None:
                current_settings.cooldown = int(settings.cooldown)
                settings_updated = True
                
            if hasattr(settings, 'max_context_length') and settings.max_context_length is not None:
                current_settings.max_context_length = int(settings.max_context_length)
                # コンテキスト履歴の最大長を更新
                context_key = f"{guild_id}:"
                for key in [k for k in self.message_history.keys() if k.startswith(context_key)]:
                    self.message_history[key] = deque(list(self.message_history[key]), maxlen=current_settings.max_context_length)
                settings_updated = True
                
            if hasattr(settings, 'ignore_bots') and settings.ignore_bots is not None:
                current_settings.ignore_bots = settings.ignore_bots
                settings_updated = True
                
            if hasattr(settings, 'ignore_prefixes') and settings.ignore_prefixes:
                if isinstance(settings.ignore_prefixes, list):
                    current_settings.ignore_prefixes = settings.ignore_prefixes
                elif isinstance(settings.ignore_prefixes, str):
                    current_settings.ignore_prefixes = settings.ignore_prefixes.split(',')
                settings_updated = True
            
            # AI応答設定
            if hasattr(settings, 'ai_enabled') and settings.ai_enabled is not None:
                current_settings.ai_enabled = settings.ai_enabled
                settings_updated = True
                
            if hasattr(settings, 'ai_temperature') and settings.ai_temperature is not None:
                current_settings.ai_temperature = float(settings.ai_temperature)
                settings_updated = True
                
            if hasattr(settings, 'ai_persona') and settings.ai_persona:
                current_settings.ai_persona = settings.ai_persona
                settings_updated = True
                
            # カスタム応答設定
            if hasattr(settings, 'custom_responses') and settings.custom_responses:
                if isinstance(settings.custom_responses, dict):
                    current_settings.custom_responses = settings.custom_responses
                    settings_updated = True
            
            # データベースに設定を保存
            if settings_updated:
                try:
                    with get_db_session() as session:
                        repo = AutoResponseSettingsRepository(session)
                        
                        # 更新データの準備
                        update_data = {
                            'enabled': current_settings.enabled,
                            'response_chance': current_settings.response_chance,
                            'cooldown': current_settings.cooldown,
                            'max_context_length': current_settings.max_context_length,
                            'ignore_bots': current_settings.ignore_bots,
                            'ignore_prefixes': current_settings.ignore_prefixes,
                            'ai_enabled': current_settings.ai_enabled,
                            'ai_temperature': current_settings.ai_temperature,
                            'ai_persona': current_settings.ai_persona
                        }
                        
                        # カスタム応答がある場合は追加
                        if current_settings.custom_responses:
                            update_data['custom_responses'] = current_settings.custom_responses
                        
                        # データベースに保存
                        success = repo.update_settings(guild_id, update_data)
                        if success:
                            self.logger.info(f"ギルド {guild_id} の自動応答設定を更新しました")
                        else:
                            self.logger.error(f"ギルド {guild_id} の自動応答設定の更新に失敗しました")
                            return False
                except Exception as e:
                    self.logger.error(f"データベース更新中にエラーが発生: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"設定更新中にエラーが発生: {e}")
            return False
    
    async def _periodic_reload_settings(self):
        """定期的に設定を再読み込み"""
        while True:
            await asyncio.sleep(3600)  # 1時間ごと
            self.logger.info("全サーバーの自動応答設定を再読み込みします")
            for guild in self.bot.guilds:
                try:
                    await self.load_guild_settings(str(guild.id))
                except Exception as e:
                    self.logger.error(f"定期再読み込み: ギルド {guild.id} の設定読み込み中にエラー: {e}")