from typing import Dict, List, Optional, Set
import discord
from datetime import datetime, timedelta
import asyncio
import logging
from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.poll')

class PollService:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        # アクティブな投票を保持する辞書
        # {message_id: {
        #     'title': str,
        #     'options': List[str],
        #     'votes': Dict[str, Set[int]],  # option: {user_ids}
        #     'expires_at': datetime,
        #     'multiple_choice': bool
        # }}
        self.active_polls: Dict[int, Dict] = {}
        # デフォルトの絵文字リスト
        self.default_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        # 投票用の特殊絵文字
        self.yes_emoji = "✅"
        self.no_emoji = "❌"

    async def create_poll(
        self,
        channel: discord.TextChannel,
        author: discord.Member,
        title: str,
        options: Optional[List[str]] = None,
        duration: Optional[int] = None,
        multiple_choice: bool = False
    ) -> Optional[discord.Message]:
        """
        新しい投票を作成します。
        
        Parameters
        ----------
        channel : discord.TextChannel
            投票を作成するチャンネル
        author : discord.Member
            投票を作成したユーザー
        title : str
            投票のタイトル
        options : List[str], optional
            選択肢のリスト（指定しない場合は賛成/反対の投票になります）
        duration : int, optional
            投票の期間（秒）
        multiple_choice : bool
            複数選択を許可するかどうか
            
        Returns
        -------
        Optional[discord.Message]
            作成された投票のメッセージ
        """
        try:
            # 投票の種類に応じてEmbedを作成
            if options:
                # 複数選択肢の投票
                if len(options) > len(self.default_emojis):
                    raise ValueError("選択肢が多すぎます（最大10個）")

                embed = discord.Embed(
                    title="📊 " + title,
                    description="リアクションで投票してください",
                    color=discord.Color.blue()
                )

                # 選択肢を追加
                for i, option in enumerate(options):
                    embed.add_field(
                        name=f"{self.default_emojis[i]} {option}",
                        value="投票数: 0",
                        inline=False
                    )

            else:
                # 賛成/反対の投票
                embed = discord.Embed(
                    title="📊 " + title,
                    description="✅ 賛成 / ❌ 反対",
                    color=discord.Color.blue()
                )
                embed.add_field(name="✅ 賛成", value="投票数: 0", inline=True)
                embed.add_field(name="❌ 反対", value="投票数: 0", inline=True)

            # 期限を設定
            expires_at = None
            if duration:
                expires_at = datetime.utcnow() + timedelta(seconds=duration)
                embed.set_footer(text=f"期限: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            else:
                embed.set_footer(text="期限なし")

            # 投票メッセージを送信
            message = await channel.send(embed=embed)

            # リアクションを追加
            if options:
                for i in range(len(options)):
                    await message.add_reaction(self.default_emojis[i])
            else:
                await message.add_reaction(self.yes_emoji)
                await message.add_reaction(self.no_emoji)

            # アクティブな投票として登録
            self.active_polls[message.id] = {
                'title': title,
                'options': options or ['yes', 'no'],
                'votes': {opt: set() for opt in (options or ['yes', 'no'])},
                'expires_at': expires_at,
                'multiple_choice': multiple_choice
            }

            # データベースに記録
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=channel.guild.id,
                    action_type="poll_create",
                    user_id=author.id,
                    target_id=message.id,
                    reason=f"投票の作成: {title}",
                    details={
                        'title': title,
                        'options': options,
                        'duration': duration,
                        'multiple_choice': multiple_choice
                    }
                )

            # 期限付きの場合、終了タスクを設定
            if duration:
                self.bot.loop.create_task(
                    self._end_poll_task(message, duration)
                )

            return message

        except Exception as e:
            logger.error(f"Failed to create poll: {e}")
            raise

    async def handle_vote(
        self,
        message_id: int,
        user_id: int,
        emoji: str
    ) -> bool:
        """
        投票を処理します。
        
        Parameters
        ----------
        message_id : int
            投票メッセージのID
        user_id : int
            投票したユーザーのID
        emoji : str
            投票に使用された絵文字
            
        Returns
        -------
        bool
            投票が成功したかどうか
        """
        if message_id not in self.active_polls:
            return False

        poll = self.active_polls[message_id]
        
        # 期限切れチェック
        if poll['expires_at'] and datetime.utcnow() > poll['expires_at']:
            return False

        # 絵文字から選択肢を特定
        if len(poll['options']) > 2:
            try:
                index = self.default_emojis.index(str(emoji))
                option = poll['options'][index]
            except (ValueError, IndexError):
                return False
        else:
            if str(emoji) == self.yes_emoji:
                option = 'yes'
            elif str(emoji) == self.no_emoji:
                option = 'no'
            else:
                return False

        # 複数選択が許可されていない場合、他の選択肢から削除
        if not poll['multiple_choice']:
            for opt in poll['votes']:
                poll['votes'][opt].discard(user_id)

        # 投票を記録
        poll['votes'][option].add(user_id)
        return True

    async def remove_vote(
        self,
        message_id: int,
        user_id: int,
        emoji: str
    ) -> bool:
        """
        投票を取り消します。
        
        Parameters
        ----------
        message_id : int
            投票メッセージのID
        user_id : int
            投票を取り消すユーザーのID
        emoji : str
            取り消す投票の絵文字
            
        Returns
        -------
        bool
            取り消しが成功したかどうか
        """
        if message_id not in self.active_polls:
            return False

        poll = self.active_polls[message_id]

        # 期限切れチェック
        if poll['expires_at'] and datetime.utcnow() > poll['expires_at']:
            return False

        # 絵文字から選択肢を特定
        if len(poll['options']) > 2:
            try:
                index = self.default_emojis.index(str(emoji))
                option = poll['options'][index]
            except (ValueError, IndexError):
                return False
        else:
            if str(emoji) == self.yes_emoji:
                option = 'yes'
            elif str(emoji) == self.no_emoji:
                option = 'no'
            else:
                return False

        # 投票を削除
        poll['votes'][option].discard(user_id)
        return True

    async def update_poll_message(self, message: discord.Message):
        """
        投票メッセージを更新します。
        
        Parameters
        ----------
        message : discord.Message
            更新する投票メッセージ
        """
        if message.id not in self.active_polls:
            return

        poll = self.active_polls[message.id]
        embed = message.embeds[0]

        # 投票結果を更新
        if len(poll['options']) > 2:
            for i, option in enumerate(poll['options']):
                votes = len(poll['votes'][option])
                embed.set_field_at(
                    i,
                    name=f"{self.default_emojis[i]} {option}",
                    value=f"投票数: {votes}",
                    inline=False
                )
        else:
            yes_votes = len(poll['votes']['yes'])
            no_votes = len(poll['votes']['no'])
            embed.set_field_at(0, name="✅ 賛成", value=f"投票数: {yes_votes}", inline=True)
            embed.set_field_at(1, name="❌ 反対", value=f"投票数: {no_votes}", inline=True)

        await message.edit(embed=embed)

    async def end_poll(self, message: discord.Message):
        """
        投票を終了します。
        
        Parameters
        ----------
        message : discord.Message
            終了する投票メッセージ
        """
        if message.id not in self.active_polls:
            return

        poll = self.active_polls[message.id]
        embed = message.embeds[0]

        # 結果を集計
        results = []
        total_votes = 0
        for option in poll['options']:
            votes = len(poll['votes'][option])
            total_votes += votes
            results.append((option, votes))

        # 結果を降順にソート
        results.sort(key=lambda x: x[1], reverse=True)

        # 結果を表示
        embed.description = "投票は終了しました\n\n**結果**"
        embed.clear_fields()

        for option, votes in results:
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            if option in ['yes', 'no']:
                name = "✅ 賛成" if option == 'yes' else "❌ 反対"
            else:
                index = poll['options'].index(option)
                name = f"{self.default_emojis[index]} {option}"
            
            embed.add_field(
                name=name,
                value=f"投票数: {votes} ({percentage:.1f}%)",
                inline=False
            )

        embed.set_footer(text=f"総投票数: {total_votes}")
        await message.edit(embed=embed)

        # アクティブな投票から削除
        del self.active_polls[message.id]

    async def _end_poll_task(self, message: discord.Message, duration: int):
        """
        投票を自動的に終了するタスク
        
        Parameters
        ----------
        message : discord.Message
            投票メッセージ
        duration : int
            投票の期間（秒）
        """
        await asyncio.sleep(duration)
        await self.end_poll(message) 