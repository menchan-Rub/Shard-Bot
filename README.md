# ShardBot

高機能なDiscordモデレーションボット

## 機能

### モデレーション機能
- BANシステム
- キックシステム
- ミュートシステム
- 警告システム
- 自動モデレーション
- レイド対策
- スパム対策

### メッセージ管理
- 一括削除
- ピン留め
- メッセージ移動
- 検索機能
- 編集履歴

### チャンネル管理
- 作成/削除
- 設定変更
- 権限設定
- 一覧表示

### ロール管理
- 作成/削除
- 付与/削除
- 設定変更
- 一覧表示

### サーバー管理
- サーバー設定
- 招待リンク管理
- 監査ログ

### ユーティリティ機能
- 翻訳機能
- タイマー機能
- 投票システム
- 計算機能

### Webダッシュボード
- サーバー統計
- ユーザー管理
- 設定管理
- ログ閲覧

## 必要要件

- Python 3.11以上
- PostgreSQL 15以上
- Redis
- Node.js 18以上

## インストール

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/shardbot.git
cd shardbot
```

2. 環境変数を設定
```bash
cp .env.example .env
# .envファイルを編集して必要な設定を行う
```

3. Dockerでの起動
```bash
docker-compose up -d
```

## 開発環境での実行

1. 依存関係のインストール
```bash
# Botの依存関係
cd bot/src
pip install -r requirements.txt

# フロントエンドの依存関係
cd ../../web/client
npm install

# バックエンドの依存関係
cd ../server
pip install -r requirements.txt
```

2. データベースのセットアップ
```bash
cd ../../bot/src
python -m alembic upgrade head
```

3. 開発サーバーの起動
```bash
# Botの起動
python main.py

# フロントエンドの起動
cd ../../web/client
npm start

# バックエンドの起動
cd ../server
uvicorn app:app --reload
```

## デプロイ

1. 本番環境用の環境変数を設定
```bash
cp .env.production.example .env.production
# .env.productionファイルを編集して本番環境の設定を行う
```

2. Dockerでデプロイ
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 作者

- 作者名
- メールアドレス
- Discordサーバー

## 謝辞

- discord.py開発者
- その他の依存ライブラリの開発者 # Shard-Bot
