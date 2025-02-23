import aiohttp
import logging
from typing import Optional, Dict, List
import os
from database.database_connection import get_db
from database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.translation')

class TranslationService:
    def __init__(self):
        """
        翻訳サービスを初期化します。
        MyMemory Translation APIを使用します。
        """
        self.base_url = "https://api.mymemory.translated.net/get"
        self.supported_languages = {
            'ja': '日本語',
            'en': '英語',
            'zh': '中国語',
            'ko': '韓国語',
            'es': 'スペイン語',
            'fr': 'フランス語',
            'de': 'ドイツ語',
            'it': 'イタリア語',
            'ru': 'ロシア語',
            'vi': 'ベトナム語'
        }
        logger.info("Translation service initialized successfully")

    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> str:
        """
        テキストを翻訳します。

        Parameters
        ----------
        text : str
            翻訳するテキスト
        target_lang : str
            翻訳先の言語コード
        source_lang : str, optional
            翻訳元の言語コード

        Returns
        -------
        str
            翻訳されたテキスト
        """
        try:
            # 言語コードを検証
            if target_lang not in self.supported_languages:
                raise ValueError(f"サポートされていない言語コードです: {target_lang}")

            if source_lang and source_lang not in self.supported_languages:
                raise ValueError(f"サポートされていない言語コードです: {source_lang}")

            # 翻訳リクエストを送信
            params = {
                'q': text,
                'langpair': f"{source_lang or 'auto'}|{target_lang}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"翻訳APIエラー: {response.status}")

                    data = await response.json()
                    if data['responseStatus'] != 200:
                        raise Exception(f"翻訳APIエラー: {data['responseStatus']}")

                    return data['responseData']['translatedText']

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    def get_supported_languages(self) -> dict:
        """
        サポートされている言語の一覧を取得します。

        Returns
        -------
        dict
            言語コードと言語名の辞書
        """
        return self.supported_languages.copy()

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> Dict[str, str]:
        """
        テキストを翻訳します。
        
        Parameters
        ----------
        text : str
            翻訳するテキスト
        target_language : str
            翻訳先の言語コード
        source_language : str, optional
            翻訳元の言語コード（指定しない場合は自動検出）
            
        Returns
        -------
        Dict[str, str]
            翻訳結果を含む辞書
        """
        try:
            # 翻訳を実行
            translated_text = await self.translate(
                text,
                target_lang=target_language,
                source_lang=source_language
            )

            return {
                'translated_text': translated_text,
                'detected_source_language': source_language or 'auto',
                'source_text': text
            }

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    def is_supported_language(self, language_code: str) -> bool:
        """
        指定された言語コードがサポートされているかチェックします。
        
        Parameters
        ----------
        language_code : str
            チェックする言語コード
            
        Returns
        -------
        bool
            サポートされているかどうか
        """
        return language_code in self.supported_languages

    def get_language_name(self, language_code: str) -> str:
        """
        言語コードから言語名を取得します。
        
        Parameters
        ----------
        language_code : str
            言語コード
            
        Returns
        -------
        str
            言語名
        """
        return self.supported_languages.get(language_code, "Unknown")

    async def detect_language(self, text: str) -> Dict[str, str]:
        """
        テキストの言語を検出します。
        
        Parameters
        ----------
        text : str
            検出するテキスト
            
        Returns
        -------
        Dict[str, str]
            検出結果を含む辞書
        """
        try:
            # 自動検出のために空の言語コードを使用
            detected_language = await self.translate(
                text,
                target_lang='',
                source_lang='auto'
            )
            return {
                'language': detected_language,
                'confidence': 1.0
            }
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise

    async def log_translation(
        self,
        guild_id: int,
        user_id: int,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str
    ):
        """
        翻訳履歴をデータベースに記録します。
        
        Parameters
        ----------
        guild_id : int
            サーバーID
        user_id : int
            ユーザーID
        source_text : str
            翻訳元テキスト
        translated_text : str
            翻訳後テキスト
        source_language : str
            翻訳元言語
        target_language : str
            翻訳先言語
        """
        try:
            async for session in get_db():
                db = DatabaseOperations(session)
                await db.create_audit_log(
                    guild_id=guild_id,
                    action_type="translation",
                    user_id=user_id,
                    target_id=None,
                    reason="テキスト翻訳",
                    details={
                        'source_text': source_text,
                        'translated_text': translated_text,
                        'source_language': source_language,
                        'target_language': target_language
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log translation: {e}") 