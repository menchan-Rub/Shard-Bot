from google.cloud import translate_v2 as translate
from typing import Optional, Dict, List
import logging
import os
from ...database.database_connection import get_db
from ...database.database_operations import DatabaseOperations

logger = logging.getLogger('utility.translation')

class TranslationService:
    def __init__(self):
        """
        翻訳サービスを初期化します。
        Google Cloud Translate APIのクライアントを作成します。
        """
        try:
            self.client = translate.Client()
            self.supported_languages = self._get_supported_languages()
            logger.info("Translation service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize translation service: {e}")
            raise

    def _get_supported_languages(self) -> Dict[str, str]:
        """
        サポートされている言語のリストを取得します。
        
        Returns
        -------
        Dict[str, str]
            言語コードと言語名の辞書
        """
        try:
            languages = self.client.get_languages()
            return {lang['language']: lang['name'] for lang in languages}
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return {}

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
            result = self.client.translate(
                text,
                target_language=target_language,
                source_language=source_language
            )

            return {
                'translated_text': result['translatedText'],
                'detected_source_language': result['detectedSourceLanguage'],
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
            detection = self.client.detect_language(text)
            return {
                'language': detection['language'],
                'confidence': detection['confidence']
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