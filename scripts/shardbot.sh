#!/bin/bash

# ShardBot サービス管理スクリプト

# 色の定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# サービス一覧
SERVICES=("postgresql" "shardbot" "shardbot-api" "nginx")

# ログファイル
LOG_DIR="/var/log/shardbot"
LOG_FILE="$LOG_DIR/service.log"

# ヘルプメッセージ
show_help() {
    echo "使用方法: $0 [コマンド]"
    echo "コマンド:"
    echo "  start    - 全サービスを起動"
    echo "  stop     - 全サービスを停止"
    echo "  restart  - 全サービスを再起動"
    echo "  status   - 全サービスの状態を表示"
    echo "  logs     - ログを表示"
    echo "  help     - このヘルプを表示"
}

# ログ出力関数
log() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} - ${message}" >> "$LOG_FILE"
    echo -e "${message}"
}

# サービスの状態確認
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}[稼働中]${NC} $service"
        return 0
    else
        echo -e "${RED}[停止中]${NC} $service"
        return 1
    fi
}

# 全サービスの起動
start_services() {
    log "${YELLOW}サービスを起動しています...${NC}"
    
    for service in "${SERVICES[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            log "起動: $service"
            sudo systemctl start "$service"
            sleep 2
        else
            log "$service は既に起動しています"
        fi
    done
    
    log "${GREEN}全サービスの起動が完了しました${NC}"
}

# 全サービスの停止
stop_services() {
    log "${YELLOW}サービスを停止しています...${NC}"
    
    # 逆順で停止（依存関係を考慮）
    for ((i=${#SERVICES[@]}-1; i>=0; i--)); do
        service="${SERVICES[$i]}"
        if systemctl is-active --quiet "$service"; then
            log "停止: $service"
            sudo systemctl stop "$service"
            sleep 2
        else
            log "$service は既に停止しています"
        fi
    done
    
    log "${GREEN}全サービスの停止が完了しました${NC}"
}

# 全サービスの再起動
restart_services() {
    log "${YELLOW}サービスを再起動しています...${NC}"
    stop_services
    sleep 5
    start_services
    log "${GREEN}全サービスの再起動が完了しました${NC}"
}

# 全サービスの状態表示
show_status() {
    echo "サービスの状態:"
    echo "----------------"
    for service in "${SERVICES[@]}"; do
        check_service "$service"
    done
}

# ログの表示
show_logs() {
    local lines=${1:-50}
    echo "最新のログ（最後の$lines行）:"
    echo "----------------"
    for service in "${SERVICES[@]}"; do
        echo -e "\n${YELLOW}=== $service のログ ===${NC}"
        sudo journalctl -u "$service" -n "$lines" --no-pager
    done
}

# メイン処理
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-50}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "不正なコマンドです"
        show_help
        exit 1
        ;;
esac

exit 0 