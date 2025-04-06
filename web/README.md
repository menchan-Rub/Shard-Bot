# Shard Bot ウェブダッシュボード

ディスコードボット「Shard Bot」のウェブダッシュボードです。サーバー設定、AIモデレーション、レイド保護、スパム保護などの機能をブラウザから簡単に設定できます。

## 構成

このウェブダッシュボードは以下の2つの部分で構成されています：

1. **バックエンド（/server）**: FastAPIを使用したREST APIサーバー
2. **フロントエンド（/client）**: React + TypeScriptで構築されたSPA（Single Page Application）

## 技術スタック

### バックエンド
- FastAPI（Python）
- SQLAlchemy（ORM）
- JWT認証
- PostgreSQL（データベース）

### フロントエンド
- React
- TypeScript
- Redux Toolkit（状態管理）
- Material-UI（UIコンポーネント）
- React Router（ルーティング）
- Axios（APIクライアント）

## セットアップ方法

### 必要条件
- Node.js (v14以上)
- npm または yarn
- Python 3.8以上
- PostgreSQL

### バックエンドの起動

1. 必要なPythonパッケージをインストール：

```bash
cd server
pip install -r requirements.txt
```

2. データベースのセットアップ：

```bash
# 環境変数の設定（またはプロジェクトルートの.envファイルを使用）
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=yourpassword
export DB_NAME=shardbot

# データベース初期化
python -m bot.src.db.migrations.create_tables
```

3. サーバーの起動：

```bash
uvicorn app:app --reload
```

### フロントエンドの起動

1. 必要なnpmパッケージをインストール：

```bash
cd client
npm install
```

2. 開発サーバーの起動：

```bash
npm start
```

アプリケーションは http://localhost:3000 で実行されます。

## 本番環境へのデプロイ

### バックエンド

```bash
cd server
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
```

### フロントエンド

```bash
cd client
npm run build
```

ビルドされたファイルは `client/build` ディレクトリに生成されます。
これらのファイルを任意のWebサーバー（Nginx、Apache等）でホスティングしてください。

## 主な機能

- Discordアカウントを使用したOAuth2ログイン
- ボットが参加しているサーバーのリスト表示
- 各サーバーごとの詳細設定
  - 一般設定（プレフィックス、言語、タイムゾーンなど）
  - AIモデレーション（有害なコンテンツの自動検出と対応）
  - 自動応答システム（カスタム応答、AI応答）
  - レイド保護（短時間での大量参加の検出と対応）
  - スパム保護（連続メッセージ、メンション、リンクなどの検出）
- ログと統計情報の表示
- ダークモード/ライトモード切り替え

## ライセンス

MIT
