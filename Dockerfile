# ベースイメージ
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 非rootユーザーを作成
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をコピーしてインストール
COPY bot/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY bot/src/ .

# 環境変数を設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 所有者を変更して、非rootユーザーに権限を付与
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェックを設定
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# コンテナ起動時のコマンドを設定
CMD ["python", "main.py"] 