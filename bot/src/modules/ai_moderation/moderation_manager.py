import discord
from discord.ext import commands
import logging
import re
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional, Union
import asyncio
from collections import defaultdict, Counter
import os
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger('modules.ai_moderation')

class AIModeration:
    """AIを使用したモデレーションシステム"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-1.0-pro')
        self.toxicity_threshold = float(os.getenv('TOXICITY_THRESHOLD', '0.8'))
        self.identity_attack_threshold = float(os.getenv('IDENTITY_ATTACK_THRESHOLD', '0.8'))
        self.insult_threshold = float(os.getenv('INSULT_THRESHOLD', '0.8'))
        self.threat_threshold = float(os.getenv('THREAT_THRESHOLD', '0.9'))
        self.sexual_threshold = float(os.getenv('SEXUAL_THRESHOLD', '0.9'))
        
        # カスタム禁止ワード
        self.custom_bad_words = os.getenv('CUSTOM_BAD_WORDS', '').split(',')
        self.custom_bad_words = [w.strip().lower() for w in self.custom_bad_words if w.strip()]
        
        # 検出時のアクション設定
        self.action_on_detect = os.getenv('AI_ACTION', 'warn')  # warn, delete, mute, kick, ban
        self.mute_duration = int(os.getenv('MUTE_DURATION', '10'))  # 分単位
        self.notify_mods = os.getenv('NOTIFY_MODS_ON_AI_DETECT', 'true').lower() == 'true'
        
        # 除外設定
        self.exclusion_roles = os.getenv('AI_EXCLUSION_ROLES', '').split(',')
        self.exclusion_roles = [r.strip() for r in self.exclusion_roles if r.strip()]
        self.exclusion_channels = os.getenv('AI_EXCLUSION_CHANNELS', '').split(',')
        self.exclusion_channels = [c.strip() for c in self.exclusion_channels if c.strip()]
        
        # キャッシュと制限
        self.checked_messages = {}  # メッセージIDをキーとした結果キャッシュ
        self.user_warning_count = {}  # ユーザーIDをキーとした警告回数
        self.rate_limit = {}  # レート制限用
        
        # Gemini APIの設定
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # 安全性設定を構成
            self.safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                }
            ]
            
            # モデルのロード
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=self.safety_settings
            )
            
            logger.info(f"Gemini AI モデレーションシステムが初期化されました: {self.model_name}")
        else:
            self.model = None
            logger.warning("Gemini API キーが設定されていないため、AIモデレーションは無効です")
        
        # フラグカウンター
        self.user_flags = defaultdict(Counter)
        self.guild_flags = defaultdict(Counter)
        
        # 最後の通知時間
        self.last_notification = {}
        
        # キャッシュ
        self.exclusion_cache = {}
        
        # API Session
        self.session = None
        
        # バックグラウンドタスク
        self.bot.loop.create_task(self._initialize())
        
    async def _initialize(self):
        """初期化処理"""
        await self.bot.wait_until_ready()
        self.session = aiohttp.ClientSession()
        logger.info("AIモデレーションシステム初期化完了")
        
    async def close(self):
        """終了処理"""
        if self.session:
            await self.session.close()
            
    async def is_excluded(self, message: discord.Message) -> bool:
        """メッセージがモデレーション対象外かどうか確認"""
        if not message.guild:
            return True  # DMは対象外
            
        # ボットは除外
        if message.author.bot:
            return True
            
        # キャッシュをチェック
        cache_key = f"{message.guild.id}:{message.author.id}:{message.channel.id}"
        if cache_key in self.exclusion_cache:
            return self.exclusion_cache[cache_key]
            
        # 除外ロールをチェック
        exclusion_roles = self.exclusion_roles
        if any(role.id in exclusion_roles for role in message.author.roles):
            self.exclusion_cache[cache_key] = True
            return True
            
        # 除外チャンネルをチェック
        exclusion_channels = self.exclusion_channels
        if message.channel.id in exclusion_channels:
            self.exclusion_cache[cache_key] = True
            return True
            
        # 管理者は除外
        if message.author.guild_permissions.administrator:
            self.exclusion_cache[cache_key] = True
            return True
            
        self.exclusion_cache[cache_key] = False
        return False
        
    async def contains_custom_bad_word(self, content: str) -> bool:
        """カスタム禁止ワードが含まれているかチェック"""
        custom_words = self.custom_bad_words
        if not custom_words:
            return False
            
        content = content.lower()
        for word in custom_words:
            if word and word.strip().lower() in content:
                return True
                
        return False
        
    async def check_message_content(self, message: discord.Message) -> Dict[str, Any]:
        """メッセージの内容をチェック"""
        if not self.api_key:
            return {'is_toxic': False, 'categories': {}, 'custom_word_detected': False}
            
        # 対象外チェック
        if await self.is_excluded(message):
            return {'is_toxic': False, 'categories': {}, 'custom_word_detected': False}
            
        content = message.content
        
        # カスタム禁止ワードチェック
        custom_word_detected = await self.contains_custom_bad_word(content)
        
        # Gemini APIによる内容チェック
        if self.model and len(content) > 5:  # 短すぎるメッセージはスキップ
            try:
                is_toxic, category, details = await self._analyze_with_gemini(content)
                if is_toxic:
                    logger.info(f"Gemini APIが有害コンテンツを検出: {category}")
                    return {
                        'is_toxic': True,
                        'categories': {category: 1.0},
                        'custom_word_detected': False,
                        'message': message,
                        'timestamp': datetime.utcnow().isoformat()
                    }
            except Exception as e:
                logger.error(f"Gemini API呼び出し中にエラーが発生: {e}")
        
        # 結果を統合
        result = {
            'is_toxic': custom_word_detected,
            'categories': {},
            'custom_word_detected': custom_word_detected,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return result
        
    async def _analyze_with_gemini(self, content: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Gemini APIを使って内容を分析"""
        # プロンプトの構築
        prompt = f"""
        次のテキストが有害かどうか分析し、JSONレスポンスで結果を返してください。

        テキスト: "{content}"

        以下のカテゴリについて、有害度が0.0から1.0のスコアで評価してください:
        1. toxicity (毒性) - 無礼、侮辱、または否定的な感情表現
        2. identity_attack (個人攻撃) - 性別、人種、宗教、その他のアイデンティティへの否定的または有害なコメント
        3. insult (侮辱) - 侮辱や軽蔑
        4. threat (脅迫) - 他者への危害を与えようとする言葉
        5. sexual (性的) - 露骨な性的な言葉や内容

        有害であるかのしきい値は、以下のとおりです:
        - toxicity: {self.toxicity_threshold}
        - identity_attack: {self.identity_attack_threshold}
        - insult: {self.insult_threshold}
        - threat: {self.threat_threshold}
        - sexual: {self.sexual_threshold}

        JSONレスポンスには以下を含めてください:
        1. is_harmful: テキスト全体が有害かどうか (Boolean)
        2. category: 最も有害度が高いカテゴリ名 (最も高いスコアのカテゴリ)
        3. reason: 有害判定の理由の簡潔な説明
        4. scores: 各カテゴリのスコア
        
        JSON形式の分析結果のみを返してください。
        """
        
        try:
            # モデルに問い合わせ
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # JSONレスポンスの抽出
            result_text = response.text
            # JSON部分の抽出（コードブロックが使用されている場合）
            json_match = re.search(r'```(?:json)?(.*?)```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text
                
            # 余分な文字を削除してJSONを抽出
            json_str = re.sub(r'^[^{]*', '', json_str)
            json_str = re.sub(r'[^}]*$', '', json_str)
            
            # JSONをパース
            result = json.loads(json_str)
            
            is_harmful = result.get('is_harmful', False)
            category = result.get('category', 'unknown')
            scores = result.get('scores', {})
            reason = result.get('reason', '')
            
            return is_harmful, category, {
                'scores': scores,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Gemini API分析中にエラーが発生: {e}")
            return False, 'error', {'reason': f'API Error: {str(e)}'}
        
    async def take_action(self, result: Dict[str, Any]) -> None:
        """検出結果に基づいて行動を実行"""
        if not result.get('is_toxic', False):
            return
            
        message = result.get('message')
        if not message or not message.guild:
            return
            
        # ユーザーとギルドのフラグカウントを更新
        user_id = message.author.id
        guild_id = message.guild.id
        
        categories = result.get('categories', {})
        for category, score in categories.items():
            if score >= 0.8:
                self.user_flags[user_id][category] += 1
                self.guild_flags[guild_id][category] += 1
                
        if result.get('custom_word_detected', False):
            self.user_flags[user_id]['custom_word'] += 1
            self.guild_flags[guild_id]['custom_word'] += 1
            
        # 実行するアクション
        action = self.action_on_detect
        
        try:
            # アクションを実行
            if action == 'delete':
                # メッセージ削除
                await message.delete()
                await self._notify_user(message.author, "不適切なコンテンツが検出されたため、メッセージは削除されました。")
                
            elif action == 'warn':
                # 警告
                await message.reply(f"{message.author.mention} 警告: 不適切なコンテンツが検出されました。サーバーのルールを確認してください。", delete_after=10)
                
            elif action == 'mute':
                # ミュート
                if hasattr(self.bot, 'moderation') and hasattr(self.bot.moderation, 'mute_member'):
                    duration = self.mute_duration  # 分単位
                    await self.bot.moderation.mute_member(message.guild, message.author, duration, "AIモデレーション: 不適切なコンテンツの検出")
                    await message.delete()
                    await self._notify_user(message.author, f"不適切なコンテンツが検出されたため、{duration}分間ミュートされました。")
                else:
                    await message.reply(f"{message.author.mention} 警告: 不適切なコンテンツが検出されました。", delete_after=10)
                    
            elif action == 'kick':
                # キック
                if message.author.guild_permissions.administrator:
                    # 管理者はキックしない
                    await message.reply(f"{message.author.mention} 警告: 不適切なコンテンツが検出されました。", delete_after=10)
                else:
                    await message.author.kick(reason="AIモデレーション: 深刻な不適切コンテンツの検出")
                    await message.delete()
                    
            elif action == 'ban':
                # BAN
                if message.author.guild_permissions.administrator:
                    # 管理者はBANしない
                    await message.reply(f"{message.author.mention} 警告: 非常に不適切なコンテンツが検出されました。", delete_after=10)
                else:
                    await message.author.ban(reason="AIモデレーション: 極めて深刻な不適切コンテンツの検出", delete_message_days=1)
                
            # モデレーターに通知
            if self.notify_mods:
                await self._notify_moderators(result)
                
            # ログに記録
            await self._log_detection(result)
                
        except discord.Forbidden:
            logger.warning(f"アクション実行のための権限がありません: {action}, サーバー: {message.guild.name}, ユーザー: {message.author}")
        except Exception as e:
            logger.error(f"アクション実行中にエラーが発生しました: {e}")
            
    async def _notify_user(self, user: discord.User, message: str) -> None:
        """ユーザーにDMで通知"""
        try:
            await user.send(message)
        except:
            # DMが無効な場合など、通知できない場合は無視
            pass
            
    async def _notify_moderators(self, result: Dict[str, Any]) -> None:
        """モデレーターに通知"""
        message = result.get('message')
        if not message or not message.guild:
            return
            
        guild = message.guild
        now = datetime.utcnow()
        
        # クールダウン確認
        cooldown_key = f"{guild.id}:notify"
        if cooldown_key in self.last_notification:
            if now - self.last_notification[cooldown_key] < timedelta(minutes=10):
                # 10分以内に通知していれば、重複通知を避ける
                return
                
        # 現在サーバーに接続しているモデレーター役職を持つメンバーを探す
        mod_role_names = ['mod', 'moderator', 'モデレーター', 'admin', 'administrator', '管理者']
        mod_roles = [role for role in guild.roles if any(name.lower() in role.name.lower() for name in mod_role_names)]
        
        # ログチャンネルを探す
        log_channel = None
        log_channel_names = ['mod-log', 'moderator-log', 'admin-log', 'モデレーターログ', 'bot-log', 'ai-moderation']
        
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and any(name.lower() in channel.name.lower() for name in log_channel_names):
                # チャンネルへの書き込み権限確認
                if channel.permissions_for(guild.me).send_messages:
                    log_channel = channel
                    break
        
        if log_channel:
            # 通知メッセージを作成
            embed = discord.Embed(
                title="🚨 AIモデレーション検出アラート",
                description=f"不適切なコンテンツが検出されました。",
                color=discord.Color.red(),
                timestamp=now
            )
            
            embed.add_field(
                name="ユーザー",
                value=f"{message.author} ({message.author.id})",
                inline=True
            )
            
            embed.add_field(
                name="チャンネル",
                value=f"{message.channel.mention} ({message.channel.id})",
                inline=True
            )
            
            embed.add_field(
                name="メッセージ内容",
                value=message.content[:1000] if message.content else "（内容なし）",
                inline=False
            )
            
            categories = result.get('categories', {})
            if categories:
                scores = "\n".join([f"{cat.capitalize()}: {score:.2f}" for cat, score in categories.items() if score > 0.5])
                embed.add_field(
                    name="検出スコア",
                    value=f"```\n{scores}\n```",
                    inline=False
                )
                
            if result.get('custom_word_detected', False):
                embed.add_field(
                    name="カスタム禁止ワード",
                    value="カスタム設定された禁止ワードが検出されました。",
                    inline=False
                )
                
            # モデレーションについての説明とリンク
            action = self.action_on_detect
            embed.add_field(
                name="実行されたアクション",
                value=f"`{action}` モードに基づいてアクションが実行されました。",
                inline=False
            )
            
            # モデレーターロールをメンション
            mod_mentions = " ".join([role.mention for role in mod_roles]) if mod_roles else ""
            
            try:
                if mod_mentions:
                    await log_channel.send(content=f"{mod_mentions} 注意: 不適切なコンテンツを検出しました。", embed=embed)
                else:
                    await log_channel.send(embed=embed)
                    
                # 通知時間を更新
                self.last_notification[cooldown_key] = now
                
            except Exception as e:
                logger.error(f"モデレーター通知の送信中にエラーが発生: {e}")
                
    async def _log_detection(self, result: Dict[str, Any]) -> None:
        """検出結果をログに記録"""
        try:
            message = result.get('message')
            if not message or not message.guild:
                return
                
            # ログディレクトリ
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            moderation_dir = os.path.join(logs_dir, 'ai_moderation')
            guild_dir = os.path.join(moderation_dir, str(message.guild.id))
            
            os.makedirs(guild_dir, exist_ok=True)
            
            # ログファイルパス
            log_file = os.path.join(guild_dir, f"{datetime.utcnow().strftime('%Y-%m')}.json")
            
            # ログデータ
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'guild_id': message.guild.id,
                'guild_name': message.guild.name,
                'channel_id': message.channel.id,
                'channel_name': message.channel.name,
                'user_id': message.author.id,
                'user_name': str(message.author),
                'message_id': message.id,
                'content': message.content,
                'is_toxic': result.get('is_toxic', False),
                'categories': result.get('categories', {}),
                'custom_word_detected': result.get('custom_word_detected', False),
                'action_taken': self.action_on_detect
            }
            
            # 既存のログを読み込むか新しいログを作成
            existing_logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except:
                    existing_logs = []
                    
            # 新しいログを追加
            existing_logs.append(log_data)
            
            # ログを保存
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"検出結果のログ記録中にエラーが発生: {e}")
            
    async def generate_report(self, guild: discord.Guild, days: int = 30) -> discord.Embed:
        """AIモデレーションレポートを生成"""
        try:
            embed = discord.Embed(
                title="🤖 AIモデレーションレポート",
                description=f"{guild.name} の過去 {days} 日間のAIモデレーション統計",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # ログディレクトリ
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            moderation_dir = os.path.join(logs_dir, 'ai_moderation')
            guild_dir = os.path.join(moderation_dir, str(guild.id))
            
            if not os.path.exists(guild_dir):
                embed.add_field(
                    name="データなし",
                    value="このサーバーのAIモデレーションログがありません。",
                    inline=False
                )
                return embed
                
            # 集計対象の期間
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # ログファイルを集める
            log_files = [f for f in os.listdir(guild_dir) if f.endswith('.json')]
            
            # データ集計
            total_detections = 0
            user_detections = Counter()
            category_counts = Counter()
            channel_counts = Counter()
            action_counts = Counter()
            
            for log_file in log_files:
                file_path = os.path.join(guild_dir, log_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                        
                    for entry in logs:
                        try:
                            # タイムスタンプをチェック
                            timestamp = datetime.fromisoformat(entry.get('timestamp', ''))
                            if timestamp < cutoff_date:
                                continue
                                
                            # 各種カウントを更新
                            total_detections += 1
                            user_detections[entry.get('user_id', 0)] += 1
                            
                            for category, score in entry.get('categories', {}).items():
                                if score >= 0.8:
                                    category_counts[category] += 1
                                    
                            if entry.get('custom_word_detected', False):
                                category_counts['custom_word'] += 1
                                
                            channel_counts[entry.get('channel_id', 0)] += 1
                            action_counts[entry.get('action_taken', 'unknown')] += 1
                            
                        except:
                            continue
                            
                except:
                    continue
            
            # レポートに追加
            embed.add_field(
                name="総検出数",
                value=str(total_detections),
                inline=True
            )
            
            embed.add_field(
                name="ユニークユーザー",
                value=str(len(user_detections)),
                inline=True
            )
            
            embed.add_field(
                name="モデレーション設定",
                value=f"アクション: `{self.action_on_detect}`",
                inline=True
            )
            
            # カテゴリ統計
            if category_counts:
                categories_text = "\n".join([f"{cat.capitalize()}: {count}" for cat, count in category_counts.most_common(5)])
                embed.add_field(
                    name="検出カテゴリ (上位5件)",
                    value=f"```\n{categories_text}\n```",
                    inline=False
                )
                
            # ユーザー統計
            if user_detections:
                user_texts = []
                for user_id, count in user_detections.most_common(5):
                    user = guild.get_member(user_id)
                    name = str(user) if user else f"ID: {user_id}"
                    user_texts.append(f"{name}: {count}件")
                    
                embed.add_field(
                    name="検出されたユーザー (上位5件)",
                    value="\n".join(user_texts),
                    inline=False
                )
                
            # チャンネル統計
            if channel_counts:
                channel_texts = []
                for channel_id, count in channel_counts.most_common(5):
                    channel = guild.get_channel(channel_id)
                    name = f"#{channel.name}" if channel else f"ID: {channel_id}"
                    channel_texts.append(f"{name}: {count}件")
                    
                embed.add_field(
                    name="検出されたチャンネル (上位5件)",
                    value="\n".join(channel_texts),
                    inline=False
                )
                
            # アクション統計
            if action_counts:
                action_text = "\n".join([f"{action}: {count}件" for action, count in action_counts.most_common()])
                embed.add_field(
                    name="実行されたアクション",
                    value=action_text,
                    inline=False
                )
                
            return embed
            
        except Exception as e:
            logger.error(f"AIモデレーションレポート生成中にエラーが発生: {e}")
            return discord.Embed(
                title="エラー",
                description=f"レポート生成中にエラーが発生しました: {e}",
                color=discord.Color.red()
            )

    async def process_message(self, message: discord.Message) -> bool:
        """
        メッセージを処理してモデレーションを行う
        
        Args:
            message: 処理するメッセージ
            
        Returns:
            bool: メッセージ処理を続行するかどうか（False=中断）
        """
        # DMは処理しない
        if not message.guild:
            return True
            
        try:
            # メッセージ内容を解析
            result = await self.check_message_content(message)
            
            # 有害コンテンツが検出された場合
            if result.get('is_toxic', False) or result.get('custom_word_detected', False):
                # アクションを実行
                await self.take_action(result)
                return False  # メッセージ処理を中断
                
        except Exception as e:
            logger.error(f"メッセージモデレーション中にエラーが発生: {e}")
        
        # 問題なければメッセージ処理を続行
        return True 