FROM python:3.11-slim

WORKDIR /app

# 必要なパッケージをインストール（ビルド時のみ必要なパッケージは別レイヤーで）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 依存関係をコピーしてインストール
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip/*

# ソースコードをコピー
COPY src/ .

# 環境変数を設定
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 不要なファイルを削除
RUN find . -type d -name "__pycache__" -exec rm -r {} + \
    && find . -type f -name "*.pyc" -delete

# 実行ユーザーを作成
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# コンテナ起動時のコマンドを設定
CMD ["python", "main.py"] 