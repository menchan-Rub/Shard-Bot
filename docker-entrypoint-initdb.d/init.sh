#!/bin/bash
set -e

# データベースが存在しない場合は作成
echo "データベースの初期化を開始します..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- シーケンスの作成（自動増分ID用）
    CREATE SEQUENCE IF NOT EXISTS global_id_seq;
    
    -- 初期設定コメント
    COMMENT ON DATABASE $POSTGRES_DB IS 'Shard Botのメインデータベース';
EOSQL

echo "データベースの初期化が完了しました" 