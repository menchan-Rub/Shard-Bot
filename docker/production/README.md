# Shard Bot 本番環境デプロイ手順

このディレクトリには、Shard Botを本番環境にデプロイするために必要な設定ファイルが含まれています。

## デプロイ前の準備

1. `.env`ファイルを本番環境用に設定する
   - 開発用の値から本番用の値に更新する
   - 特に`DISCORD_BOT_TOKEN`と`GEMINI_API_KEY`が正しく設定されていることを確認する
   - `DB_SSL_MODE=require`に設定する
   - `DASHBOARD_URL`を実際の本番環境URLに更新する
   - `DEV_MODE=false`に設定する

2. SSL証明書の準備
   - Let's Encryptなどでサーバー用の証明書を取得
   - 取得した証明書ファイルを`docker/production/nginx/ssl/`ディレクトリに配置:
     - `fullchain.pem`
     - `privkey.pem`
     - `chain.pem`
   - DHパラメータの生成:
     ```
     openssl dhparam -out docker/production/nginx/ssl/dhparam.pem 2048
     ```

3. フロントエンドビルド
   ```
   cd web/client
   npm install
   npm run build
   ```
   ビルドしたファイルを`docker/production/nginx/www/`ディレクトリにコピー

## デプロイ手順

1. コンテナのビルドと起動
   ```
   cd docker/production
   docker-compose build
   docker-compose up -d
   ```

2. 初期セットアップの確認
   ```
   docker-compose logs -f bot
   ```
   ログを確認し、正常に起動していることを確認する

3. データベースマイグレーションの実行（必要な場合）
   ```
   docker-compose exec bot python -m bot.src.db.migrations.create_tables
   ```

## 監視とメンテナンス

1. ログの確認
   ```
   docker-compose logs -f
   ```

2. コンテナの状態確認
   ```
   docker-compose ps
   ```

3. メモリ使用量の確認
   ```
   docker stats
   ```

4. バックアップの実行（週次推奨）
   ```
   docker-compose exec postgres pg_dump -U postgres shardbot > backup_$(date +%Y%m%d).sql
   ```

## トラブルシューティング

1. コンテナが起動しない場合
   - ログを確認: `docker-compose logs -f <サービス名>`
   - 環境変数の確認: `.env`ファイルの設定を再確認
   - ネットワーク設定の確認: `docker network ls`

2. Discordボットが接続できない場合
   - トークンの確認: `.env`の`DISCORD_BOT_TOKEN`が正しいか確認
   - インテントの設定: Discordデベロッパーポータルでの権限設定を確認

3. Webダッシュボードにアクセスできない場合
   - Nginxのログを確認: `docker-compose logs -f nginx`
   - SSL証明書の確認: 証明書ファイルが正しく配置されているか確認
   - ポート転送の確認: サーバーのファイアウォール設定を確認

## システム要件

- Docker: 20.10.x以上
- Docker Compose: 2.x以上
- ストレージ: 最低10GB
- メモリ: 最低4GB
- CPU: 2コア以上推奨 