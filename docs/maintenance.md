# ShardBot メンテナンスガイド

## 日常的なメンテナンス

### 1. ログの管理

```bash
# ログファイルの確認
tail -f /var/log/shardbot/bot.log
tail -f /var/log/shardbot/api.log

# エラーログの確認
tail -f /var/log/shardbot/error.log
tail -f /var/log/shardbot/api-error.log

# Nginxログの確認
tail -f /var/log/nginx/shardbot-access.log
tail -f /var/log/nginx/shardbot-error.log
```

### 2. バックアップ

```bash
# データベースのバックアップ
pg_dump -U menchan shardbot > backup/shardbot_$(date +%Y%m%d).sql

# 設定ファイルのバックアップ
cp /home/menchan/shardbot/.env backup/env_$(date +%Y%m%d)
```

### 3. アップデート

```bash
# Botの更新
cd /home/menchan/shardbot/bot
source venv/bin/activate
pip install -r src/requirements.txt --upgrade
deactivate

# APIの更新
cd /home/menchan/shardbot/dashboard/server
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# フロントエンドの更新
cd /home/menchan/shardbot/dashboard/client
npm install
npm run build

# サービスの再起動
sudo systemctl restart shardbot shardbot-api
```

## 定期的なメンテナンス

### 1. データベースの最適化

```bash
# PostgreSQLの統計情報更新
sudo -u postgres vacuumdb --analyze --all

# テーブルの断片化チェック
sudo -u postgres psql -d shardbot -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### 2. ディスク使用量の管理

```bash
# ディスク使用量の確認
df -h
du -sh /home/menchan/shardbot/*

# 古いログファイルの削除
find /var/log/shardbot -name "*.log.*" -mtime +30 -delete
```

### 3. セキュリティ更新

```bash
# システムの更新
sudo apt update
sudo apt upgrade -y

# Pythonパッケージの脆弱性チェック
source bot/venv/bin/activate
pip list --outdated
safety check
deactivate

# npmパッケージの脆弱性チェック
cd dashboard/client
npm audit
```

## トラブルシューティング

### 1. サービスの異常停止

```bash
# ステータス確認
sudo systemctl status shardbot
sudo systemctl status shardbot-api

# ログの確認
journalctl -u shardbot -n 100
journalctl -u shardbot-api -n 100
```

### 2. データベース接続エラー

```bash
# PostgreSQLのステータス確認
sudo systemctl status postgresql

# 接続テスト
psql -U menchan -d shardbot -c "\l"
```

### 3. メモリ使用量の監視

```bash
# メモリ使用量の確認
free -h
top -u menchan

# プロセスの監視
ps aux | grep python
```

### 4. ネットワーク接続の確認

```bash
# APIの接続確認
curl -I http://localhost:8000/health

# Discordの接続確認
ping discord.com
```

## 緊急時の対応

### 1. サービスの緊急停止

```bash
sudo systemctl stop shardbot shardbot-api
```

### 2. データベースのリストア

```bash
# データベースの再作成
sudo -u postgres dropdb shardbot
sudo -u postgres createdb shardbot

# バックアップからリストア
psql -U menchan -d shardbot < backup/shardbot_YYYYMMDD.sql
```

### 3. ログの保全

```bash
# ログファイルのアーカイブ
tar -czf logs_$(date +%Y%m%d_%H%M%S).tar.gz /var/log/shardbot/
``` 