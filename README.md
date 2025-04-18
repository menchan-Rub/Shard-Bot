# Shard Bot

モダンな機能を搭載したDiscordモデレーションボット

## 主な機能

- **AIモデレーション**: Google Gemini AI APIを使用した高度なコンテンツモデレーション
- **自動応答システム**: カスタムトリガーとAI応答を使用したインテリジェントな応答
- **レイド保護**: 急速なサーバー参加の検出と自動対応
- **スパム保護**: メッセージスパム、メンション、リンクの検出と対応
- **ウェブダッシュボード**: すべての設定をブラウザから簡単に管理
- **カスタマイズ可能**: サーバーごとにカスタマイズできる設定
- **コマンドラインツール**: 便利な管理用CLIツール

## システム要件

- Python 3.8以上
- PostgreSQL
- Redis (オプション、キャッシュと一時データ用)
- Node.js 14以上 (ウェブダッシュボード用)

## インストール方法

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/shard-bot.git
cd shard-bot
```

### 2. 環境のセットアップ

#### 依存パッケージのインストール

```bash
pip install -r requirements.txt

# ウェブダッシュボード用の依存パッケージ
cd web/client
npm install
cd ../..
```

#### 環境変数の設定

1. `config/example.env` を `.env` という名前でプロジェクトのルートディレクトリにコピー
2. `.env` ファイルを編集して必要な設定（DiscordトークンなどのAPI認証情報）を入力

### 3. データベースのセットアップ

```bash
# データベース初期化
python -m bot.src.db.migrations.create_tables
```

### 4. ボットの起動

```bash
# ボットの起動
python -m bot.src.main

# ウェブダッシュボードの起動
cd web/server
uvicorn app:app --host 0.0.0.0 --port 8000 &
cd ../client
npm start
```

### 5. コマンドラインツールのインストール（オプション）

Shard Botには、ボットを簡単に管理するためのコマンドラインツールが付属しています。
このツールをシステムワイドにインストールするには、以下のコマンドを実行します：

#### システム全体へのインストール（管理者権限が必要）

```bash
# システム全体へのインストール（管理者権限が必要）
sudo ./scripts/install.sh
```

#### ユーザーのホームディレクトリへのインストール

```bash
# ユーザーのホームディレクトリへのインストール
./scripts/local-install.sh
```

インストール後は、任意のディレクトリから以下のコマンドが使用できます：

```bash
# ヘルプの表示
shardbot help

# ボットの起動
shardbot start bot

# すべてのサービスの状態確認
shardbot status

# API/Webダッシュボードの起動
shardbot start api
shardbot start web

# ログの確認
shardbot logs bot 100

# 追加コマンド
shardbot deploy        # 全サービスをビルド＆デプロイ
shardbot update        # コードをアップデートして再デプロイ
shardbot check         # 環境と設定の健全性チェック
shardbot prune         # 未使用のDockerリソースを削除
```

## Docker Composeによる実行

Shard Botは、Docker Composeを使用して簡単にデプロイできます。

```bash
# 全サービスの起動
docker-compose up -d

# 特定のサービスのみ起動
docker-compose up -d bot db

# 状態確認
docker-compose ps

# ログの確認
docker-compose logs --tail=100 bot
```

あるいは、コマンドラインツールを使用してDockerの操作を簡素化できます：

```bash
shardbot deploy    # ビルドと起動を一度に行う
shardbot status    # サービスの状態を確認
```

## 設定

Shard Botは、Webダッシュボードを使用して簡単に設定することができます。もしくは直接データベースや設定ファイルを編集することもできます。

### Webダッシュボード

ブラウザで `http://localhost:3000` にアクセスしてダッシュボードを開き、Discordアカウントでログインします。
ダッシュボードでは以下の設定を管理できます：

- サーバー基本設定
- AIモデレーション設定
- 自動応答設定
- レイド保護設定
- スパム保護設定
- ログと統計情報

### 環境変数

詳細な設定オプションについては `.env` ファイルのコメントを参照してください。主な設定項目：

- `DISCORD_BOT_TOKEN`: ボットのDiscordトークン
- `CLIENT_ID`: DiscordアプリケーションのID
- `CLIENT_SECRET`: Discordアプリケーションシークレット
- `DB_*`: データベース接続設定
- `REDIS_*`: Redis接続設定（オプション）
- `DASHBOARD_*`: ウェブダッシュボード設定
- `GEMINI_API_KEY`: Google Gemini API キー

## モジュール

Shard Botは以下のモジュールで構成されています：

1. **コアモジュール** - ボットの基本機能
2. **AIモデレーション** - AIを使用したコンテンツモデレーション
3. **自動応答** - メッセージへの自動応答
4. **レイド保護** - レイド検出と対応
5. **スパム保護** - スパム検出と対応
6. **ウェブダッシュボード** - 設定管理用のUIインターフェース

## ライセンス

MIT

## 貢献

貢献は歓迎します！問題点の報告やプルリクエストなど、お気軽にご協力ください。

## 機能

### モデレーション機能
- BANシステム
- キックシステム
- ミュートシステム
- 警告システム
- 自動モデレーション
- レイド対策
- スパム対策
- 高度なレイド検知と自動対応
- スマートスパム検出
- 自動ミュート機能
- AIパワードモデレーション
- カスタム禁止ワード管理
- 学習型コンテンツフィルター

### メッセージ管理
- 一括削除
- ピン留め
- メッセージ移動
- 検索機能
- 編集履歴
- メッセージログ
- 統計レポート
- 添付ファイル管理
- 自動応答システム
- AIチャット応答機能
- コンテキスト認識会話

### チャンネル管理
- 作成/削除
- 設定変更
- 権限設定
- 一覧表示
- カテゴリ管理
- 自動アーカイブ設定
- スロットモード
- 動的音声チャンネル
- プライベートチャンネル
- テンプレートシステム

### ロール管理
- 作成/削除
- 付与/削除
- 設定変更
- 一覧表示
- 階層管理
- カラー管理
- 自動ロール
- リアクションロール
- 排他的ロールグループ
- 一時的ロール付与

### サーバー管理
- サーバー設定
- 招待リンク管理
- 監査ログ
- メンバー統計
- アクティビティ追跡
- セキュリティ設定
- ウェルカムメッセージ
- 退出メッセージ
- メンバー認証システム
- サーバーバックアップ

### ユーティリティ機能
- 翻訳機能
- タイマー機能
- 投票システム
- 計算機能
- メモ機能
- 予定表
- リマインダー
- イベント管理システム
- カレンダー連携
- RSVP機能

### Webダッシュボード
- サーバー統計
- ユーザー管理
- 設定管理
- ログ閲覧
- カスタムコマンド管理
- ボット状態監視
- エラー分析
- 2段階認証
- カスタムテーマ
- モバイル対応UI
- 高度な分析ダッシュボード

### 新機能
- 高度なエラー分析と通知システム
- メッセージ履歴検索と分析
- リッチ統計レポート生成
- スマートスパム検出機能
- 強化されたレイド対策
- 自動復旧モード
- 細かいパフォーマンス改善
- 多様なRich Presence表示
- 強化されたログシステム
- AIパワードモデレーション
- 自動応答システム
- 動的音声チャンネル管理
- イベント管理システム
- リアクションロールの強化
- カレンダー連携機能
- ウェルカム/退出メッセージのカスタマイズ

## 必要要件

- Python 3.11以上
- PostgreSQL 15以上
- Redis
- Node.js 18以上

## 設定ガイド

Shard-Botは高度にカスタマイズ可能です。以下の設定で細かく動作を調整できます。

### スパム対策設定
- メッセージ速度制限
- メンション制限
- 添付ファイル制限
- 大文字制限
- URL制限
- 自動ミュート機能

### レイド対策設定
- 参加率検出
- 新規アカウント制限
- レイドモード自動発動
- 検証レベル自動調整
- チャンネルロックダウン

### AIモデレーション設定
- 毒性検出閾値
- カスタム禁止ワード
- アクション設定
- モデレーター通知
- 除外ロール/チャンネル

### 自動応答設定
- 応答確率
- カスタム応答パターン
- AIパワード応答
- コンテキスト長設定
- クールダウン期間

### 音声チャンネル設定
- 自動チャンネル作成
- テンプレート名
- 自動削除
- ユーザー権限
- プライベートチャンネル

### イベント管理設定
- イベントカテゴリ
- RSVP機能
- リマインダータイミング
- チャンネル自動作成
- カレンダー連携

詳細は[設定ドキュメント](docs/configuration.md)を参照してください。

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
- その他の依存ライブラリの開発者

## 詳細機能

### エラーロギング
- **メッセージロギング**: サーバー内のメッセージを記録し、モデレーション目的で保存します。

### AIモデレーション

AIを活用して不適切なメッセージを検出し、自動的に対処する機能です。

- **API連携**: OpenAIのContentFilterなどのAPIと連携して高精度な検出が可能です
- **カスタムキーワード**: サーバー固有の禁止ワードを設定できます
- **段階的対応**: 警告、削除、ミュート、キック、BANなど段階的な対応が可能です
- **モデレーター通知**: 検出時にモデレーターに通知できます
- **除外設定**: 特定の役割や管理者を除外できます

### 自動応答システム

メッセージに対して自動的に応答する機能を提供します。

- **カスタム応答**: 特定のキーワードに対する応答パターンを設定できます
- **AI応答**: OpenAIのAPIを活用した自然な会話応答が可能です
- **コンテキスト認識**: 会話の流れを考慮した応答ができます
- **確率ベース**: 一定確率で応答することで、自然なコミュニケーションを実現します
- **クールダウン**: チャンネルごとのクールダウンで、応答頻度を調整できます
- **統計レポート**: 応答パターンや頻度を分析したレポートを生成できます

## データベース構成

Shard Botは以下のデータを保存します:

- **Guilds**: サーバー情報
- **GuildSettings**: サーバーごとの基本設定
- **ModerationSettings**: AIモデレーション設定
- **AutoResponseSettings**: 自動応答設定
- **RaidSettings**: Raid対策設定
- **SpamSettings**: スパム対策設定
- **Users**: ダッシュボードユーザー情報
- **AuditLogs**: 監査ログ

## Docker での起動方法

Shard Bot はDockerとDocker Composeを使用して簡単に起動できます。マルチステージビルドを採用し、開発・本番環境それぞれに最適化された構成を用意しています。

### 準備

1. 環境変数ファイルを作成
```bash
cp .env.example .env
```

2. `.env`ファイルを編集して必要な情報（Discordトークンなど）を入力

### Makefile を使った簡単操作

```bash
# ヘルプを表示
make help

# 開発環境で起動（ライブリロード対応）
make dev

# 本番環境で起動
make up

# コンテナを停止
make down

# ログを表示
make logs

# ボットコンテナに接続
make shell

# データベースに接続
make db-shell
```

### 手動での操作

#### 開発環境

開発環境では、ホスト上のコードの変更がコンテナ内に反映されます。

```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

#### 本番環境

本番環境では、ビルド時のコードがコンテナにパッケージングされます。

```bash
docker-compose up -d
```

### システム要件

- Docker Engine 20.10以上
- Docker Compose 2.0以上
- 最小ハードウェア要件:
  - CPU: 2コア
  - メモリ: 2GB以上
  - ディスク: 10GB以上

## 環境設定

Shard Botはテスト環境と本番環境を簡単に切り替えて使用できます。

### 環境の切り替え

同梱の`setup.sh`スクリプトを使用して、簡単に環境を切り替えることができます：

```bash
# テスト環境をセットアップ
./setup.sh test

# 本番環境をセットアップ
./setup.sh prod

# 現在の環境を確認
./setup.sh status
```

### 環境の起動と停止

```bash
# 環境を起動
./setup.sh start

# 環境を停止
./setup.sh stop

# 環境を再起動
./setup.sh restart

# ログを表示
./setup.sh logs
```

### 環境の違い

| 設定項目 | テスト環境 | 本番環境 |
|---------|-----------|---------|
| データベース | `postgres-test` | `postgres` |
| Redis | `redis-test` | `redis` |
| ダッシュボードURL | http://localhost:8080 | https://dashboard.shardbot.com |
| SSL | 無効 | 有効 |
| ログレベル | DEBUG | INFO |
| 開発モード | 有効 | 無効 |
