# ShardBot セキュリティガイド

## 基本的なセキュリティ設定

### 1. ファイルのパーミッション

```bash
# 適切なパーミッションの設定
chmod 750 /home/menchan/shardbot
chmod 640 /home/menchan/shardbot/.env
chmod 750 /home/menchan/shardbot/bot/venv
chmod 750 /home/menchan/shardbot/dashboard/server/venv

# ログディレクトリの設定
sudo mkdir -p /var/log/shardbot
sudo chown -R menchan:menchan /var/log/shardbot
chmod 750 /var/log/shardbot
```

### 2. ファイアウォール設定

```bash
# 必要なポートのみ開放
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# 設定の確認
sudo ufw status verbose
```

### 3. SSH設定

```bash
# SSHの設定変更
sudo nano /etc/ssh/sshd_config

# 推奨設定
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Protocol 2
```

## セキュリティ監視

### 1. ログの監視

```bash
# 不正アクセスの監視
sudo tail -f /var/log/auth.log
sudo tail -f /var/log/nginx/shardbot-access.log

# 異常なアクセスパターンの検出
sudo grep "Failed password" /var/log/auth.log
```

### 2. システムの監視

```bash
# プロセスの監視
ps aux | grep -E "python|node|nginx"

# ポートの監視
sudo netstat -tulpn | grep -E "8000|80|443"

# ディスク使用量の監視
df -h
```

## セキュリティ更新

### 1. システムの更新

```bash
# セキュリティアップデート
sudo apt update
sudo apt upgrade -y
sudo apt dist-upgrade -y

# 不要なパッケージの削除
sudo apt autoremove -y
sudo apt clean
```

### 2. アプリケーションの更新

```bash
# Pythonパッケージの更新
source bot/venv/bin/activate
pip list --outdated
pip install --upgrade pip setuptools wheel
deactivate

# npmパッケージの更新
cd dashboard/client
npm audit fix
npm update
```

## セキュリティベストプラクティス

### 1. パスワード管理

- 強力なパスワードの使用（最低16文字、特殊文字を含む）
- 定期的なパスワードの変更
- パスワードマネージャーの使用

### 2. アクセス制御

- 最小権限の原則に従う
- 不要なサービスの無効化
- アクセスログの定期的な監査

### 3. データ保護

- 機密情報の暗号化
- 定期的なバックアップ
- アクセス制御リストの適切な設定

### 4. インシデント対応

1. 異常の検知
   - ログの監視
   - システムリソースの監視
   - ネットワークトラフィックの監視

2. 初期対応
   - 影響範囲の特定
   - 必要に応じたサービスの停止
   - ログの保全

3. 復旧手順
   - バックアップからのリストア
   - セキュリティパッチの適用
   - 設定の見直し

4. 事後対応
   - インシデントの分析
   - 再発防止策の実施
   - 文書化と報告 