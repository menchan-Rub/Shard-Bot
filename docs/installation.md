# ShardBot インストールガイド

## システム要件

- Ubuntu 22.04 LTS以降
- Python 3.11以降
- PostgreSQL 14以降
- Node.js 18以降（フロントエンド開発用）

## システム構成

```
/home/menchan/shardbot/
├── bot/              # Discord Bot
│   ├── src/         # ソースコード
│   └── venv/        # Bot用の仮想環境
├── dashboard/        # Webダッシュボード
│   ├── client/      # フロントエンド
│   ├── server/      # バックエンドAPI
│   └── venv/        # ダッシュボード用の仮想環境
└── systemd/         # システムサービス設定
```

## セットアップ手順

### 1. システムの依存関係インストール

```bash
# システムの更新
sudo apt update
sudo apt upgrade -y

# 必要なパッケージのインストール
sudo apt install -y python3.11 python3.11-venv postgresql nginx
```

### 2. PostgreSQLのセットアップ

```bash
# データベースとユーザーの作成
sudo -u postgres createdb shardbot
sudo -u postgres createuser -P menchan  # パスワードを設定

# データベース接続設定の変更
sudo nano /etc/postgresql/14/main/pg_hba.conf
# 以下の行を追加
# local   shardbot    menchan                             md5
```

### 3. Bot環境のセットアップ

```bash
# 仮想環境の作成と有効化
python3.11 -m venv bot/venv
source bot/venv/bin/activate

# 依存関係のインストール
pip install -r bot/src/requirements.txt
deactivate
```

### 4. ダッシュボード環境のセットアップ

```bash
# バックエンド
python3.11 -m venv dashboard/server/venv
source dashboard/server/venv/bin/activate
pip install -r dashboard/server/requirements.txt
deactivate

# フロントエンド
cd dashboard/client
npm install
npm run build
```

### 5. 環境変数の設定

`.env`ファイルを作成し、必要な環境変数を設定：

```bash
cp .env.example .env
nano .env
```

### 6. サービスの起動

```bash
# サービスの有効化と起動
sudo systemctl enable shardbot shardbot-api
sudo systemctl start shardbot shardbot-api

# ステータスの確認
sudo systemctl status shardbot
sudo systemctl status shardbot-api
```

## トラブルシューティング

1. データベース接続エラー
   - PostgreSQLのサービスが起動しているか確認
   - データベースの認証設定を確認
   - 環境変数の設定を確認

2. Bot起動エラー
   - Discordトークンの有効性を確認
   - 必要な権限が付与されているか確認
   - ログを確認（`journalctl -u shardbot`）

3. API起動エラー
   - ポート8000が利用可能か確認
   - データベース接続設定を確認
   - ログを確認（`journalctl -u shardbot-api`）

4. フロントエンドの表示エラー
   - Nginxの設定を確認
   - ビルドが正常に完了しているか確認
   - ブラウザのコンソールでエラーを確認 