# コマンドの読み込み
async def load_commands(manager):
    # ... existing code ...
    
    # 自動応答コマンドの読み込み
    await manager.load_extension('bot.src.commands.auto_response')
    
    # ... existing code ... 