#!/bin/bash

# Shard-Bot 環境セットアップスクリプト

# カラー設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 使用方法を表示
show_usage() {
  echo -e "${YELLOW}使用方法:${NC}"
  echo -e "  $0 [環境]"
  echo -e ""
  echo -e "${YELLOW}環境:${NC}"
  echo -e "  test     - テスト環境をセットアップ"
  echo -e "  prod     - 本番環境をセットアップ"
  echo -e "  status   - 現在の環境を表示"
  echo -e "  start    - 現在の環境を起動"
  echo -e "  stop     - 現在の環境を停止"
  echo -e "  restart  - 現在の環境を再起動"
  echo -e "  logs     - ログを表示"
  echo -e ""
  echo -e "${YELLOW}例:${NC}"
  echo -e "  $0 test    # テスト環境をセットアップ"
  echo -e "  $0 start   # 環境を起動"
}

# 現在の環境を確認
check_current_env() {
  if [ -L .env ] && [ -e .env ]; then
    CURRENT_ENV=$(readlink .env)
    if [[ "$CURRENT_ENV" == ".env.test" ]]; then
      echo "test"
    elif [[ "$CURRENT_ENV" == ".env.production" ]]; then
      echo "prod"
    else
      echo "unknown"
    fi
  else
    echo "none"
  fi
}

# 環境をセットアップ
setup_environment() {
  ENV=$1
  
  # 既存の.envファイルのリンクを削除
  if [ -L .env ]; then
    rm .env
  fi
  
  if [ "$ENV" == "test" ]; then
    ln -s .env.test .env
    echo -e "${GREEN}テスト環境をセットアップしました${NC}"
  elif [ "$ENV" == "prod" ]; then
    ln -s .env.production .env
    echo -e "${GREEN}本番環境をセットアップしました${NC}"
  else
    echo -e "${RED}無効な環境です: $ENV${NC}"
    show_usage
    exit 1
  fi
}

# 環境を起動
start_environment() {
  CURRENT_ENV=$(check_current_env)
  
  if [ "$CURRENT_ENV" == "test" ]; then
    echo -e "${BLUE}テスト環境を起動しています...${NC}"
    cd docker/test && docker-compose up -d
  elif [ "$CURRENT_ENV" == "prod" ]; then
    echo -e "${BLUE}本番環境を起動しています...${NC}"
    cd docker/production && docker-compose up -d
  else
    echo -e "${RED}環境が設定されていません。'$0 test' または '$0 prod' を実行してください。${NC}"
    exit 1
  fi
}

# 環境を停止
stop_environment() {
  CURRENT_ENV=$(check_current_env)
  
  if [ "$CURRENT_ENV" == "test" ]; then
    echo -e "${BLUE}テスト環境を停止しています...${NC}"
    cd docker/test && docker-compose down
  elif [ "$CURRENT_ENV" == "prod" ]; then
    echo -e "${BLUE}本番環境を停止しています...${NC}"
    cd docker/production && docker-compose down
  else
    echo -e "${RED}環境が設定されていません。'$0 test' または '$0 prod' を実行してください。${NC}"
    exit 1
  fi
}

# 環境を再起動
restart_environment() {
  stop_environment
  start_environment
}

# ログを表示
show_logs() {
  CURRENT_ENV=$(check_current_env)
  
  if [ "$CURRENT_ENV" == "test" ]; then
    echo -e "${BLUE}テスト環境のログを表示しています...${NC}"
    cd docker/test && docker-compose logs -f
  elif [ "$CURRENT_ENV" == "prod" ]; then
    echo -e "${BLUE}本番環境のログを表示しています...${NC}"
    cd docker/production && docker-compose logs -f
  else
    echo -e "${RED}環境が設定されていません。'$0 test' または '$0 prod' を実行してください。${NC}"
    exit 1
  fi
}

# 環境のステータスを表示
show_status() {
  CURRENT_ENV=$(check_current_env)
  
  if [ "$CURRENT_ENV" == "test" ]; then
    echo -e "${GREEN}現在の環境: テスト環境${NC}"
    cd docker/test && docker-compose ps
  elif [ "$CURRENT_ENV" == "prod" ]; then
    echo -e "${GREEN}現在の環境: 本番環境${NC}"
    cd docker/production && docker-compose ps
  elif [ "$CURRENT_ENV" == "none" ]; then
    echo -e "${YELLOW}環境が設定されていません。'$0 test' または '$0 prod' を実行してください。${NC}"
  else
    echo -e "${RED}不明な環境: $CURRENT_ENV${NC}"
  fi
}

# メイン処理
if [ $# -eq 0 ]; then
  show_usage
  exit 1
fi

COMMAND=$1

case $COMMAND in
  test)
    setup_environment "test"
    ;;
  prod)
    setup_environment "prod"
    ;;
  start)
    start_environment
    ;;
  stop)
    stop_environment
    ;;
  restart)
    restart_environment
    ;;
  logs)
    show_logs
    ;;
  status)
    show_status
    ;;
  *)
    echo -e "${RED}不明なコマンド: $COMMAND${NC}"
    show_usage
    exit 1
    ;;
esac

exit 0 