# ビルドステージ
FROM node:18-alpine as builder

WORKDIR /app

# パッケージ設定ファイルをコピー
COPY dashboard/package*.json ./

# 依存関係のインストール
RUN npm ci

# ソースコードのコピー
COPY dashboard/ ./

# Next.jsアプリをビルド
RUN npm run build

# 実行ステージ
FROM node:18-alpine

WORKDIR /app

# ビルド済みのアプリケーションをコピー
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.js ./

# 実行ユーザーを作成
RUN adduser -D appuser
USER appuser

# 環境変数の設定
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# Next.jsを本番モードで実行
CMD ["npm", "run", "start"] 