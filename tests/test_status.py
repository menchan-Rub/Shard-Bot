import sys
import os
import time
import unittest
import discord
from discord.ext import commands

# sys.pathにbot/src/commands/utilityを追加して、Status Cogをインポート
current_dir = os.path.dirname(os.path.abspath(__file__))
utility_path = os.path.join(current_dir, '..', 'bot', 'src', 'commands', 'utility')
if utility_path not in sys.path:
    sys.path.insert(0, utility_path)

from status import Status


class FakeBot:
    def __init__(self):
        self.guilds = []


class FakeContext:
    def __init__(self):
        self.sent_embed = None

    async def send(self, embed):
        self.sent_embed = embed
        return embed


class TestStatusCog(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake_bot = FakeBot()
        # テスト用にguildsを設定
        self.fake_bot.guilds = ['guild1', 'guild2']
        self.cog = Status(self.fake_bot)
        self.ctx = FakeContext()
        
    async def test_status_command(self):
        # statusコマンドを呼び出す
        await self.cog.status(self.ctx)
        # 送信されたembedを取得
        embed = self.ctx.sent_embed
        self.assertIsNotNone(embed, 'Embedが送信されていることを確認')
        self.assertEqual(embed.title, 'Bot Status', 'Embedのタイトルが正しいことを確認')
        
        # embedのフィールドから値を取得
        fields = {field.name: field.value for field in embed.fields}
        self.assertIn('Uptime', fields, 'Uptimeフィールドが存在すること')
        self.assertIn('Guilds', fields, 'Guildsフィールドが存在すること')
        self.assertIn('Memory Usage', fields, 'Memory Usageフィールドが存在すること')
        
        # FakeBotでguildsは2となっているので、Guildsフィールドの値が'2'であることを確認
        self.assertEqual(fields['Guilds'], '2', 'Guildsフィールドの値が正しいこと')

if __name__ == '__main__':
    unittest.main() 