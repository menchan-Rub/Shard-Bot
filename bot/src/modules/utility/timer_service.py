import asyncio
from datetime import datetime
import logging
from discord.ext import commands
from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.timer_service')

class TimerService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.running = False
        self.current_task = None

    async def start(self):
        """タイマーサービスを開始します"""
        self.running = True
        self.current_task = asyncio.create_task(self._timer_loop())
        logger.info("Timer service started")

    async def stop(self):
        """タイマーサービスを停止します"""
        self.running = False
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        logger.info("Timer service stopped")

    async def _timer_loop(self):
        """タイマーの監視ループ"""
        while self.running:
            try:
                await self._check_timers()
                # 1分ごとにチェック
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in timer loop: {e}")
                await asyncio.sleep(60)  # エラー時も1分待機

    async def _check_timers(self):
        """期限切れのタイマーをチェックして処理します"""
        async for session in get_db():
            db = DatabaseOperations(session)
            expired_timers = await db.get_expired_timers()

            for timer in expired_timers:
                try:
                    # タイマーのメッセージを送信
                    channel = self.bot.get_channel(timer.channel_id)
                    if channel:
                        await channel.send(timer.message)

                    # 繰り返しタイマーの場合は次回の時刻を設定
                    if timer.is_recurring and timer.interval:
                        next_time = datetime.utcnow()
                        while next_time <= datetime.utcnow():
                            next_time = next_time + timedelta(seconds=timer.interval)

                        await db.create_timer(
                            guild_id=timer.guild_id,
                            channel_id=timer.channel_id,
                            user_id=timer.user_id,
                            expires_at=next_time,
                            message=timer.message,
                            is_recurring=True,
                            interval=timer.interval
                        )

                    # 使用済みタイマーを削除
                    await session.execute(
                        f"DELETE FROM timers WHERE id = {timer.id}"
                    )
                    await session.commit()

                except Exception as e:
                    logger.error(f"Error processing timer {timer.id}: {e}")

    async def create_timer(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        expires_at: datetime,
        message: str,
        is_recurring: bool = False,
        interval: int = None
    ):
        """
        新しいタイマーを作成します
        
        Parameters
        ----------
        guild_id : int
            サーバーID
        channel_id : int
            チャンネルID
        user_id : int
            ユーザーID
        expires_at : datetime
            タイマーの期限
        message : str
            送信するメッセージ
        is_recurring : bool, optional
            繰り返しタイマーかどうか
        interval : int, optional
            繰り返し間隔（秒）
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_timer(
                    guild_id=guild_id,
                    channel_id=channel_id,
                    user_id=user_id,
                    expires_at=expires_at,
                    message=message,
                    is_recurring=is_recurring,
                    interval=interval
                )
            logger.info(f"Created timer for user {user_id} in guild {guild_id}")
        except Exception as e:
            logger.error(f"Error creating timer: {e}")
            raise

    async def cancel_timer(self, timer_id: int):
        """
        タイマーをキャンセルします
        
        Parameters
        ----------
        timer_id : int
            タイマーID
        """
        try:
            async for session in get_db():
                await session.execute(
                    f"DELETE FROM timers WHERE id = {timer_id}"
                )
                await session.commit()
            logger.info(f"Cancelled timer {timer_id}")
        except Exception as e:
            logger.error(f"Error cancelling timer {timer_id}: {e}")
            raise

    async def get_user_timers(self, user_id: int, guild_id: int):
        """
        ユーザーのタイマー一覧を取得します
        
        Parameters
        ----------
        user_id : int
            ユーザーID
        guild_id : int
            サーバーID
            
        Returns
        -------
        List[Timer]
            タイマーのリスト
        """
        try:
            async for session in get_db():
                result = await session.execute(
                    f"SELECT * FROM timers WHERE user_id = {user_id} AND guild_id = {guild_id}"
                )
                return result.fetchall()
        except Exception as e:
            logger.error(f"Error getting timers for user {user_id}: {e}")
            raise 