import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os
from typing import Optional, Dict, Any, Tuple
import yaml
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('ShardBot')

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# 環境変数の読み込み
load_dotenv()

# 環境変数のバリデーション
def validate_env_vars():
    required_vars = ['DISCORD_TOKEN', 'SETUP_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set them in your .env file"
        )

# 設定ファイルの読み込み
def load_config(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class ShardBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',  # デフォルトのプレフィックス
            intents=intents,
            help_command=None,  # カスタムヘルプコマンドを使用
        )
        self.logger = logger
        
    async def setup_hook(self) -> None:
        """ボットの初期設定を行います"""
        # コマンドの読み込み
        await self.load_extensions()
        
        # データベース接続の確認
        # TODO: データベース接続の実装
        
    async def load_extensions(self):
        """全ての拡張機能を読み込みます"""
        for folder in ['commands', 'events']:
            for root, _, files in os.walk(f'src/{folder}'):
                for file in files:
                    if file.endswith('.py'):
                        extension = os.path.join(root, file) \
                            .replace('/', '.').replace('\\', '.')[:-3]
                        try:
                            await self.load_extension(extension)
                            self.logger.info(f'Loaded extension: {extension}')
                        except Exception as e:
                            self.logger.error(f'Failed to load extension {extension}: {e}')

    async def on_ready(self):
        """ボットが準備完了したときに呼ばれます"""
        self.logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        self.logger.info('------')

    # キャプチャ生成
    def generate_captcha(self, length: int = 4) -> Tuple[str, io.BytesIO]:
        code = ''.join(random.choices(string.digits, k=length))
        width, height = 120, 60
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except Exception:
            font = ImageFont.load_default()
        text_width, text_height = draw.textsize(code, font=font)
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        draw.text((x, y), code, font=font, fill=(0, 0, 0))
        for _ in range(10):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line(((x1, y1), (x2, y2)), fill=(0, 0, 0), width=1)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        return code, image_bytes

    # プログレスバーの生成
    def build_progress_bar(self, current: int, total: int, bar_length: int = 20) -> str:
        filled = int((bar_length * current) // total)
        return "[" + "█" * filled + "░" * (bar_length - filled) + f"] {int(100 * current / total)}%"

async def main():
    """メイン関数"""
    # 環境変数のバリデーション
    validate_env_vars()
    
    # ボットの起動
    async with ShardBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main()) 