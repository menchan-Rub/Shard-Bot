.PHONY: help build up down logs ps shell db-shell redis-shell clean

# デフォルトのターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  make build        - Dockerイメージをビルド"
	@echo "  make up           - コンテナを起動"
	@echo "  make down         - コンテナを停止"
	@echo "  make logs         - ログを表示"
	@echo "  make ps           - 実行中のコンテナを表示"
	@echo "  make shell        - ボットコンテナにシェルで接続"
	@echo "  make db-shell     - PostgreSQLコンテナに接続"
	@echo "  make redis-shell  - Redisコンテナに接続"
	@echo "  make clean        - 未使用のイメージとボリュームを削除"
	@echo "  make dev          - 開発環境でコンテナを起動"

# イメージをビルド
build:
	docker-compose build

# コンテナを起動（本番環境）
up:
	docker-compose up -d

# 開発環境でコンテナを起動
dev:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# コンテナを停止
down:
	docker-compose down

# ログを表示
logs:
	docker-compose logs -f

# 実行中のコンテナを表示
ps:
	docker-compose ps

# ボットコンテナにシェルで接続
shell:
	docker-compose exec bot bash

# PostgreSQLコンテナに接続
db-shell:
	docker-compose exec postgres psql -U postgres shardbot

# Redisコンテナに接続
redis-shell:
	docker-compose exec redis redis-cli

# クリーンアップ：未使用のイメージとボリュームを削除
clean:
	docker system prune -f
	docker volume prune -f 