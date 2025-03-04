#!/bin/bash

# 設定
PROJECT_DIR="/home/menchan/Programming/Discord/Shard-Bot"
BOT_DIR="$PROJECT_DIR/bot"
API_DIR="$PROJECT_DIR/web/server"
CLIENT_DIR="$PROJECT_DIR/web/client"
LOG_DIR="$PROJECT_DIR/logs"

# PIDファイル
BOT_PID_FILE="/tmp/shardbot.pid"
API_PID_FILE="/tmp/shardbot-api.pid"
CLIENT_PID_FILE="/tmp/shardbot-client.pid"

# ログファイル
mkdir -p "$LOG_DIR"
BOT_LOG="$LOG_DIR/bot.log"
API_LOG="$LOG_DIR/api.log"
CLIENT_LOG="$LOG_DIR/client.log"
NGINX_LOG="/var/log/nginx/shardbot.log"
PG_LOG="/var/log/postgresql/postgresql-15-main.log"

# 色とスタイルの設定を拡張
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

# プロセスの検出（改善版）
find_process() {
    local name=$1
    local port=$2
    
    if [ -n "$port" ]; then
        # ポート番号でプロセスを検索
        pid=$(lsof -t -i:$port 2>/dev/null)
        if [ -n "$pid" ]; then
            echo "$pid"
            return 0
        fi
    fi
    
    # プロセス名で検索
    pids=$(pgrep -f "$name" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids"
        return 0
    fi
    
    return 1
}

# プロセスの停止（改善版）
kill_process() {
    local name=$1
    local pids=$2
    
    if [ -z "$pids" ]; then
        return 0
    fi
    
    echo -e "${BLUE}${name}を停止しています...${NC}"
    
    # まずSIGTERMで停止を試みる
    kill $pids 2>/dev/null
    
    # プロセスの終了を待つ（最大10秒）
    for i in {1..10}; do
        if ! ps -p $pids >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    
    # 強制終了
    echo -e "${YELLOW}${name}が応答しないため、強制終了します...${NC}"
    kill -9 $pids 2>/dev/null
    
    # 最終確認
    if ps -p $pids >/dev/null 2>&1; then
        echo -e "${RED}${name}の停止に失敗しました${NC}"
        return 1
    fi
    
    return 0
}

# サービスの状態確認（改善版）
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        return 0  # 実行中
    fi
    return 1  # 停止中
}

# PostgreSQLの管理
manage_postgresql() {
    local action=$1
    case "$action" in
        start)
            echo -e "${BLUE}PostgreSQLを起動しています...${NC}"
            sudo systemctl start postgresql
            ;;
        stop)
            echo -e "${BLUE}PostgreSQLを停止しています...${NC}"
            sudo systemctl stop postgresql
            ;;
        restart)
            echo -e "${BLUE}PostgreSQLを再起動しています...${NC}"
            sudo systemctl restart postgresql
            ;;
        status)
            if check_service postgresql; then
                echo -e "${GREEN}PostgreSQL: 実行中${NC}"
            else
                echo -e "${RED}PostgreSQL: 停止中${NC}"
            fi
            ;;
    esac
}

# Nginxの管理
manage_nginx() {
    local action=$1
    case "$action" in
        start)
            echo -e "${BLUE}Nginxを起動しています...${NC}"
            sudo systemctl start nginx
            ;;
        stop)
            echo -e "${BLUE}Nginxを停止しています...${NC}"
            sudo systemctl stop nginx
            ;;
        restart)
            echo -e "${BLUE}Nginxを再起動しています...${NC}"
            sudo systemctl restart nginx
            ;;
        status)
            if check_service nginx; then
                echo -e "${GREEN}Nginx: 実行中${NC}"
            else
                echo -e "${RED}Nginx: 停止中${NC}"
            fi
            ;;
    esac
}

# Discord Botの管理（改善版）
manage_bot() {
    local action=$1
    case "$action" in
        start)
            local bot_pid=$(find_process "python.*src/main.py")
            if [ -n "$bot_pid" ]; then
                echo -e "${YELLOW}ShardBotは既に実行中です (PID: $bot_pid)${NC}"
                return
            fi
            echo -e "${BLUE}ShardBotを起動しています...${NC}"
            cd "$BOT_DIR" && \
            source venv/bin/activate && \
            python src/main.py >> "$BOT_LOG" 2>&1 &
            bot_pid=$!
            echo $bot_pid > "$BOT_PID_FILE"
            ;;
        stop)
            local bot_pid=$(find_process "python.*src/main.py")
            if [ -n "$bot_pid" ]; then
                kill_process "ShardBot" "$bot_pid"
                rm -f "$BOT_PID_FILE"
            fi
            ;;
        restart)
            echo -e "${BLUE}ShardBotを再起動しています...${NC}"
            manage_bot stop
            sleep 2
            manage_bot start
            ;;
        status)
            local bot_pid=$(find_process "python.*src/main.py")
            if [ -n "$bot_pid" ]; then
                echo -e "${GREEN}ShardBot: 実行中 (PID: $bot_pid)${NC}"
            else
                echo -e "${RED}ShardBot: 停止中${NC}"
            fi
            ;;
    esac
}

# APIサーバーの管理（改善版）
manage_api() {
    local action=$1
    case "$action" in
        start)
            local api_pid=$(find_process "uvicorn.*main:app" "8000")
            if [ -n "$api_pid" ]; then
                echo -e "${YELLOW}API Serverは既に実行中です (PID: $api_pid)${NC}"
                return
            fi
            echo -e "${BLUE}API Serverを起動しています...${NC}"
            cd "$API_DIR" && \
            python3 -m venv venv && \
            source venv/bin/activate && \
            pip install -r requirements.txt && \
            uvicorn main:app --host 0.0.0.0 --port 8000 >> "$API_LOG" 2>&1 &
            api_pid=$!
            echo $api_pid > "$API_PID_FILE"
            ;;
        stop)
            local api_pid=$(find_process "uvicorn.*main:app" "8000")
            if [ -n "$api_pid" ]; then
                kill_process "API Server" "$api_pid"
                rm -f "$API_PID_FILE"
            fi
            ;;
        restart)
            echo -e "${BLUE}API Serverを再起動しています...${NC}"
            manage_api stop
            sleep 2
            manage_api start
            ;;
        status)
            local api_pid=$(find_process "uvicorn.*main:app" "8000")
            if [ -n "$api_pid" ]; then
                echo -e "${GREEN}API Server: 実行中 (PID: $api_pid)${NC}"
            else
                echo -e "${RED}API Server: 停止中${NC}"
            fi
            ;;
    esac
}

# フロントエンドの管理（改善版）
manage_client() {
    local action=$1
    case "$action" in
        start)
            local client_pid=$(find_process "node.*react-scripts.*start" "8080")
            if [ -n "$client_pid" ]; then
                echo -e "${YELLOW}Frontend Serverは既に実行中です (PID: $client_pid)${NC}"
                return
            fi
            echo -e "${BLUE}Frontend Serverを起動しています...${NC}"
            cd "$CLIENT_DIR" && npm run dev >> "$CLIENT_LOG" 2>&1 &
            client_pid=$!
            echo $client_pid > "$CLIENT_PID_FILE"
            ;;
        stop)
            local client_pid=$(find_process "node.*react-scripts.*start" "8080")
            if [ -n "$client_pid" ]; then
                kill_process "Frontend Server" "$client_pid"
                rm -f "$CLIENT_PID_FILE"
            fi
            ;;
        restart)
            echo -e "${BLUE}Frontend Serverを再起動しています...${NC}"
            manage_client stop
            sleep 2
            manage_client start
            ;;
        status)
            local client_pid=$(find_process "node.*react-scripts.*start" "8080")
            if [ -n "$client_pid" ]; then
                echo -e "${GREEN}Frontend Server: 実行中 (PID: $client_pid)${NC}"
            else
                echo -e "${RED}Frontend Server: 停止中${NC}"
            fi
            ;;
    esac
}

# 全サービスの管理
manage_all() {
    local action=$1
    case "$action" in
        start)
            echo -e "${YELLOW}全サービスを起動しています...${NC}"
            manage_postgresql start
            sleep 2
            manage_bot start
            sleep 2
            manage_api start
            sleep 2
            manage_client start
            sleep 2
            manage_nginx start
            ;;
        stop)
            echo -e "${YELLOW}全サービスを停止しています...${NC}"
            manage_nginx stop
            sleep 1
            manage_client stop
            sleep 1
            manage_api stop
            sleep 1
            manage_bot stop
            sleep 1
            manage_postgresql stop
            ;;
        restart)
            echo -e "${YELLOW}全サービスを再起動しています...${NC}"
            manage_all stop
            sleep 2
            manage_all start
            ;;
        status)
            show_header
            echo -e "${BOLD}${WHITE}システムステータス${NC}"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            
            # PostgreSQL状態確認
            if check_service postgresql; then
                echo -e "  ${BOLD}PostgreSQL${NC}  │ ${GREEN}●${NC} 実行中"
            else
                echo -e "  ${BOLD}PostgreSQL${NC}  │ ${RED}●${NC} 停止中"
            fi
            
            # Bot状態確認
            local bot_pid=$(find_process "python.*src/main.py")
            if [ -n "$bot_pid" ]; then
                echo -e "  ${BOLD}ShardBot${NC}    │ ${GREEN}●${NC} 実行中 ${DIM}(PID: $bot_pid)${NC}"
            else
                echo -e "  ${BOLD}ShardBot${NC}    │ ${RED}●${NC} 停止中"
            fi
            
            # API状態確認
            local api_pid=$(find_process "uvicorn.*main:app" "8000")
            if [ -n "$api_pid" ]; then
                echo -e "  ${BOLD}API Server${NC}  │ ${GREEN}●${NC} 実行中 ${DIM}(PID: $api_pid)${NC}"
            else
                echo -e "  ${BOLD}API Server${NC}  │ ${RED}●${NC} 停止中"
            fi
            
            # Frontend状態確認
            local client_pid=$(find_process "node.*react-scripts.*start" "8080")
            if [ -n "$client_pid" ]; then
                echo -e "  ${BOLD}Frontend${NC}    │ ${GREEN}●${NC} 実行中 ${DIM}(PID: $client_pid)${NC}"
            else
                echo -e "  ${BOLD}Frontend${NC}    │ ${RED}●${NC} 停止中"
            fi
            
            # Nginx状態確認
            if check_service nginx; then
                echo -e "  ${BOLD}Nginx${NC}       │ ${GREEN}●${NC} 実行中"
            else
                echo -e "  ${BOLD}Nginx${NC}       │ ${RED}●${NC} 停止中"
            fi
            
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;
    esac
}

# ログの表示
show_logs() {
    local service=$1
    local lines=${2:-50}
    
    case "$service" in
        bot)
            if [ -f "$BOT_LOG" ]; then
                echo -e "${YELLOW}Bot logs (最新の$lines行):${NC}"
                tail -n "$lines" "$BOT_LOG"
            fi
            ;;
        api)
            if [ -f "$API_LOG" ]; then
                echo -e "${YELLOW}API logs (最新の$lines行):${NC}"
                tail -n "$lines" "$API_LOG"
            fi
            ;;
        client)
            if [ -f "$CLIENT_LOG" ]; then
                echo -e "${YELLOW}Frontend logs (最新の$lines行):${NC}"
                tail -n "$lines" "$CLIENT_LOG"
            fi
            ;;
        nginx)
            if [ -f "$NGINX_LOG" ]; then
                echo -e "${YELLOW}Nginx logs (最新の$lines行):${NC}"
                sudo tail -n "$lines" "$NGINX_LOG"
            fi
            ;;
        postgresql)
            if [ -f "$PG_LOG" ]; then
                echo -e "${YELLOW}PostgreSQL logs (最新の$lines行):${NC}"
                sudo tail -n "$lines" "$PG_LOG"
            fi
            ;;
        all)
            echo -e "${YELLOW}全サービスのログ (最新の$lines行):${NC}"
            for s in bot api client nginx postgresql; do
                echo -e "\n${BLUE}=== $s のログ ===${NC}"
                show_logs "$s" "$lines"
            done
            ;;
        *)
            echo -e "${RED}無効なサービス名です${NC}"
            echo "使用可能なサービス: bot, api, client, nginx, postgresql, all"
            return 1
            ;;
    esac
}

# ヘルプの表示
show_help() {
    show_header
    echo -e "${BOLD}${WHITE}使用方法:${NC}"
    echo -e "  shardbot ${CYAN}<command>${NC} ${YELLOW}[service]${NC} ${PURPLE}[options]${NC}"
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
    echo -e "  ${YELLOW}client${NC}      フロントエンド"
    echo -e "  ${YELLOW}nginx${NC}       Nginxサーバー"
    echo -e "  ${YELLOW}postgresql${NC}  PostgreSQLデータベース"
    echo
    echo -e "${BOLD}${WHITE}例:${NC}"
    echo -e "  ${DIM}shardbot start${NC}           全サービスを起動"
    echo -e "  ${DIM}shardbot stop bot${NC}        Botのみ停止"
    echo -e "  ${DIM}shardbot status api${NC}      APIの状態を確認"
    echo -e "  ${DIM}shardbot logs client 100${NC} フロントエンドの最新100行"
}

# メインの処理
case "$1" in
    start|stop|restart|status)
        service=${2:-all}
        case "$service" in
            all)
                manage_all "$1"
                ;;
            bot)
                manage_bot "$1"
                ;;
            api)
                manage_api "$1"
                ;;
            client)
                manage_client "$1"
                ;;
            nginx)
                manage_nginx "$1"
                ;;
            postgresql)
                manage_postgresql "$1"
                ;;
            *)
                echo -e "${RED}無効なサービス名です${NC}"
                echo "使用可能なサービス: all, bot, api, client, nginx, postgresql"
                exit 1
                ;;
        esac
        ;;
    logs)
        service=${2:-all}
        lines=${3:-50}
        show_logs "$service" "$lines"
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