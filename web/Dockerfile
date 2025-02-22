# ビルドステージ
FROM node:18-alpine as builder

WORKDIR /app

# 依存関係のインストール
COPY client/package*.json ./
RUN npm install

# ソースコードのコピーとビルド
COPY client/ .
RUN npm run build

# 実行ステージ
FROM node:18-alpine

WORKDIR /app

# serveパッケージをグローバルにインストール
RUN npm install -g serve

# ビルドしたファイルをコピー
COPY --from=builder /app/build ./build

# 実行ユーザーを作成
RUN adduser -D appuser
USER appuser

# 環境変数の設定
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# serveを使用して静的ファイルを配信
CMD ["serve", "-s", "build", "-l", "3000"] 