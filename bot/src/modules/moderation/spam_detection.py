import discord
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger('ShardBot.Moderation.SpamDetection')

try:
    from database import get_db
    database_available = True
except ImportError:
    logger.warning("データベースモジュールが利用できません。スパム検知の一部機能が制限されます。")
    database_available = False

class SpamDetector:
    """スパム検知を行うクラス"""
    
    def __init__(self):
        # メッセージ履歴を保持する辞書
        self.message_history: Dict[int, List[Tuple[float, str]]] = defaultdict(list)
        # スパム判定済みのユーザーを保持するセット
        self.spam_users: Set[int] = set()
        # スパム判定のしきい値
        self.threshold = 5  # 5秒以内
        self.max_similar_messages = 3  # 類似メッセージの最大数
        
    def _cleanup_history(self, user_id: int) -> None:
        """古いメッセージ履歴を削除"""
        current_time = time.time()
        self.message_history[user_id] = [
            (t, m) for t, m in self.message_history[user_id]
            if current_time - t <= self.threshold
        ]
    
    def _is_similar(self, msg1: str, msg2: str) -> bool:
        """2つのメッセージが類似しているかを判定"""
        # 完全一致の場合
        if msg1 == msg2:
            return True
            
        # 長さが大きく異なる場合は類似していないと判定
        if abs(len(msg1) - len(msg2)) > min(len(msg1), len(msg2)) * 0.3:
            return False
            
        # 文字の一致率を計算
        common_chars = sum(1 for c in msg1 if c in msg2)
        similarity = common_chars / max(len(msg1), len(msg2))
        
        return similarity > 0.8
    
    async def detect_spam(self, message: discord.Message) -> bool:
        """メッセージがスパムかどうかを判定"""
        user_id = message.author.id
        current_time = time.time()
        content = message.content
        
        # スパム判定済みのユーザーの場合
        if user_id in self.spam_users:
            return True
        
        # 履歴のクリーンアップ
        self._cleanup_history(user_id)
        
        # 類似メッセージのカウント
        similar_count = 1  # 現在のメッセージを含む
        for _, msg in self.message_history[user_id]:
            if self._is_similar(content, msg):
                similar_count += 1
                if similar_count > self.max_similar_messages:
                    self.spam_users.add(user_id)
                    
                    # データベースが利用可能な場合、スパム記録を保存
                    if database_available:
                        try:
                            async with get_db() as db:
                                # スパム記録をデータベースに保存するロジック
                                pass
                        except Exception as e:
                            logger.error(f"スパム記録の保存に失敗: {e}")
                    
                    return True
        
        # 履歴に追加
        self.message_history[user_id].append((current_time, content))
        return False
    
    def remove_spam_user(self, user_id: int) -> None:
        """ユーザーをスパム判定リストから削除"""
        self.spam_users.discard(user_id)
        self.message_history.pop(user_id, None)