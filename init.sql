-- データベースとユーザーの作成
CREATE DATABASE shardbot;

-- 拡張機能のインストール
\c shardbot
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- シーケンスの作成（自動増分ID用）
CREATE SEQUENCE IF NOT EXISTS global_id_seq;

-- 初期設定コメント
COMMENT ON DATABASE shardbot IS 'Shard Botのメインデータベース'; 