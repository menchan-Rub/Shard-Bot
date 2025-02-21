from discord.ext import commands
from discord import app_commands
import discord
from typing import Optional, List
import logging
from ...modules.utility.translation_service import TranslationService

logger = logging.getLogger('utility.translate')

class Translate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translation_service = TranslationService()
        # 翻訳用の絵文字
        self.translation_emoji = "🌐"

    @app_commands.command(name="translate", description="テキストを翻訳します")
    @app_commands.describe(
        text="翻訳するテキスト",
        target_language="翻訳先の言語コード（例: en, ja, ko）",
        source_language="翻訳元の言語コード（指定しない場合は自動検出）"
    )
    async def translate(
        self,
        interaction: discord.Interaction,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ):
        """
        テキストを翻訳します。
        
        Parameters
        ----------
        text : str
            翻訳するテキスト
        target_language : str
            翻訳先の言語コード
        source_language : str, optional
            翻訳元の言語コード
        """
        await interaction.response.defer()

        try:
            # 言語コードの検証
            if not self.translation_service.is_supported_language(target_language):
                await interaction.followup.send(
                    f"無効な翻訳先言語コードです: {target_language}",
                    ephemeral=True
                )
                return

            if source_language and not self.translation_service.is_supported_language(source_language):
                await interaction.followup.send(
                    f"無効な翻訳元言語コードです: {source_language}",
                    ephemeral=True
                )
                return

            # 翻訳を実行
            result = await self.translation_service.translate_text(
                text=text,
                target_language=target_language,
                source_language=source_language
            )

            # 翻訳結果を表示
            embed = discord.Embed(
                title="翻訳結果",
                color=discord.Color.blue()
            )
            embed.add_field(
                name=f"原文 ({result['detected_source_language']})",
                value=result['source_text'],
                inline=False
            )
            embed.add_field(
                name=f"翻訳 ({target_language})",
                value=result['translated_text'],
                inline=False
            )
            embed.set_footer(text=f"翻訳者: {interaction.user}")

            await interaction.followup.send(embed=embed)

            # 翻訳履歴を記録
            await self.translation_service.log_translation(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                source_text=result['source_text'],
                translated_text=result['translated_text'],
                source_language=result['detected_source_language'],
                target_language=target_language
            )

        except Exception as e:
            await interaction.followup.send(
                "翻訳中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Translation failed: {e}")

    @app_commands.command(name="languages", description="サポートされている言語の一覧を表示します")
    async def languages(self, interaction: discord.Interaction):
        """サポートされている言語の一覧を表示します"""
        try:
            languages = self.translation_service.supported_languages
            
            # 言語リストを作成
            language_list = [
                f"`{code}`: {name}"
                for code, name in sorted(languages.items())
            ]

            # 25言語ごとにフィールドを分割
            chunks = [language_list[i:i + 25] for i in range(0, len(language_list), 25)]

            embed = discord.Embed(
                title="サポートされている言語",
                color=discord.Color.blue()
            )

            for i, chunk in enumerate(chunks, 1):
                embed.add_field(
                    name=f"言語一覧 {i}",
                    value="\n".join(chunk),
                    inline=True
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                "言語一覧の取得中にエラーが発生しました。",
                ephemeral=True
            )
            logger.error(f"Failed to get language list: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        リアクションが追加されたときの処理
        翻訳用の絵文字が付けられた場合、メッセージを翻訳します
        """
        if str(payload.emoji) != self.translation_emoji:
            return

        try:
            # メッセージを取得
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(payload.message_id)
            if not message or not message.content:
                return

            # リアクションを付けたユーザーを取得
            user = self.bot.get_user(payload.user_id)
            if not user or user.bot:
                return

            # 言語を検出
            detection = await self.translation_service.detect_language(message.content)
            target_language = "en" if detection['language'] == "ja" else "ja"

            # 翻訳を実行
            result = await self.translation_service.translate_text(
                text=message.content,
                target_language=target_language
            )

            # 翻訳結果を表示
            embed = discord.Embed(
                title="翻訳結果",
                color=discord.Color.blue()
            )
            embed.add_field(
                name=f"原文 ({result['detected_source_language']})",
                value=result['source_text'],
                inline=False
            )
            embed.add_field(
                name=f"翻訳 ({target_language})",
                value=result['translated_text'],
                inline=False
            )
            embed.set_footer(text=f"翻訳者: {user}")

            await message.reply(embed=embed)

            # 翻訳履歴を記録
            await self.translation_service.log_translation(
                guild_id=payload.guild_id,
                user_id=user.id,
                source_text=result['source_text'],
                translated_text=result['translated_text'],
                source_language=result['detected_source_language'],
                target_language=target_language
            )

        except Exception as e:
            logger.error(f"Failed to handle translation reaction: {e}")

async def setup(bot: commands.Bot):
    """Cogを登録"""
    await bot.add_cog(Translate(bot)) 