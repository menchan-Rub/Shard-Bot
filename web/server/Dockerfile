FROM python:3.10-slim

WORKDIR /app

# 依存関係をインストール
COPY web/server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# redisパッケージを追加インストール
RUN pip install --no-cache-dir redis

# Webサーバーのソースコードをコピー
COPY web/server/ .

# ボットのソースコードをコピー
COPY bot/ ./bot/

# 環境変数を設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ポート8000を公開
EXPOSE 8000

# FastAPIを起動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 