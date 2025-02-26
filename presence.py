from pypresence import Presence
import time

# Discord Developer Portalで作成したアプリケーションのClient ID
CLIENT_ID = "1344209317624152095"

try:
    # RPCクライアントの初期化
    RPC = Presence(CLIENT_ID)
    
    # RPCクライアントの接続
    RPC.connect()
    
    print("Discord RPCに接続しました。")
    
    # ビジュアライザーの設定に合わせた更新
    RPC.update(
        state="Playing Solo",
        details="Competitive",
        start=1507665886,
        end=1507665886,
        large_image="shard_logo",
        large_text="Numbani",
        party_id="ae488379-351d-4a4f-ad32-2b9b01c",
        party_size=[1, 5],
        join="MTI4NzM0OjFpMmhuZToxMjMxMjM"
    )
    
    print("Rich Presenceを設定しました。")
    print("Ctrl+Cで終了できます。")
    
    # プログラムを実行し続ける
    while True:
        time.sleep(15)
        
except KeyboardInterrupt:
    print("\nRich Presenceを終了します。")
    if 'RPC' in locals():
        RPC.close()
except Exception as e:
    print(f"エラーが発生しました: {e}")
    print("エラーの詳細:", str(e.__class__.__name__))
    if 'RPC' in locals():
        RPC.close()