#!/bin/bash

# 設定
PROJECT_DIR="/home/menchan/Programming/Discord/Shard-Bot"
cd "$PROJECT_DIR" || exit 1

LOG_DIR="$PROJECT_DIR/logs"

# ログディレクトリの作成
mkdir -p "$LOG_DIR"

# 色とスタイルの設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ヘッダー表示
show_header() {
    echo -e "${BOLD}${CYAN}ShardBot${NC} ${DIM}v1.0.0${NC}"
    echo
}

# ヘルプの表示
show_help() {
    show_header
    echo -e "${BOLD}${WHITE}使用方法:${NC}"
    echo -e "  shardbot <command> [service] [options]"
    echo
    echo -e "${BOLD}${WHITE}コマンド:${NC}"
    echo -e "  ${CYAN}start${NC}    ${YELLOW}[service]${NC}    サービスを起動"
    echo -e "  ${CYAN}stop${NC}     ${YELLOW}[service]${NC}    サービスを停止"
    echo -e "  ${CYAN}restart${NC}  ${YELLOW}[service]${NC}    サービスを再起動"
    echo -e "  ${CYAN}status${NC}   ${YELLOW}[service]${NC}    サービスの状態を表示"
    echo -e "  ${CYAN}logs${NC}     ${YELLOW}<service>${NC} ${PURPLE}[n]${NC}  ログを表示"
    echo
    echo -e "${BOLD}${WHITE}サービス:${NC}"
    echo -e "  ${YELLOW}all${NC}         全てのサービス ${DIM}(デフォルト)${NC}"
    echo -e "  ${YELLOW}bot${NC}         Discord Bot"
    echo -e "  ${YELLOW}api${NC}         APIサーバー"
    echo -e "  ${YELLOW}web${NC}         Webダッシュボード"
    echo -e "  ${YELLOW}nginx${NC}       Nginxサーバー"
    echo -e "  ${YELLOW}postgresql${NC}  PostgreSQLデータベース"
    echo
    echo -e "${BOLD}${WHITE}例:${NC}"
    echo -e "  ${DIM}shardbot start${NC}             全サービスを起動"
    echo -e "  ${DIM}shardbot stop bot${NC}          Botのみ停止"
    echo -e "  ${DIM}shardbot status api${NC}        APIの状態を確認"
    echo -e "  ${DIM}shardbot logs web 100${NC}     Webダッシュボードの最新100行"
}

# Docker Compose コマンドの実行関数
run_docker_compose() {
    docker-compose "$@"
}

# 全サービスの管理
manage_all() {
    local action=$1
    case "$action" in
        start)
            echo -e "${BLUE}全サービスを起動しています...${NC}"
            run_docker_compose up -d
            ;;
        stop)
            echo -e "${YELLOW}全サービスを停止しています...${NC}"
            run_docker_compose stop
            ;;
        restart)
            echo -e "${BLUE}全サービスを再起動しています...${NC}"
            run_docker_compose restart
            ;;
        status)
            run_docker_compose ps
            ;;
        *)
            echo -e "${RED}無効なアクションです${NC}"
            ;;
    esac
}

# 個別サービスの管理
manage_service() {
    local service=$1
    local action=$2
    case "$action" in
        start)
            echo -e "${BLUE}${service}を起動しています...${NC}"
            run_docker_compose up -d "$service"
            ;;
        stop)
            echo -e "${YELLOW}${service}を停止しています...${NC}"
            run_docker_compose stop "$service"
            ;;
        restart)
            echo -e "${BLUE}${service}を再起動しています...${NC}"
            run_docker_compose restart "$service"
            ;;
        status)
            echo -e "${BLUE}${service} の状態を確認しています...${NC}"
            run_docker_compose ps | grep "$service" || echo -e "${YELLOW}サービス ${service} が見つかりません${NC}"
            ;;
        *)
            echo -e "${RED}無効なアクションです: $action${NC}"
            ;;
    esac
}

# ログの表示
show_logs() {
    local service=$1
    local lines=${2:-50}
    echo -e "${YELLOW}${service} logs (最新の${lines}行):${NC}"
    run_docker_compose logs --tail="$lines" "$service"
}

# メインの処理
case "$1" in
    start|stop|restart|status)
        service=${2:-all}
        if [ "$service" = "all" ]; then
            manage_all "$1"
        else
            manage_service "$service" "$1"
        fi
        ;;
    logs)
        service=${2:-all}
        lines=${3:-50}
        if [ "$service" = "all" ]; then
            run_docker_compose logs --tail="$lines"
        else
            show_logs "$service" "$lines"
        fi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}無効なコマンドです${NC}"
        show_help
        exit 1
        ;;
esac