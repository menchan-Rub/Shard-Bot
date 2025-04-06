FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 依存関係インストール用のファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# 環境変数設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ポート8080を公開（APIサーバー用）
EXPOSE 8080

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# デフォルトでBotを起動（docker-compose.ymlでオーバーライド可能）
CMD ["python", "-m", "bot.src.main"] 