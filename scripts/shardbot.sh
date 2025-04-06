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
    echo -e "  ${CYAN}deploy${NC}                全サービスをデプロイ (ビルド→起動)"
    echo -e "  ${CYAN}update${NC}                コードの更新とデプロイを実行"
    echo -e "  ${CYAN}check${NC}                 環境と設定の健全性チェック"
    echo -e "  ${CYAN}prune${NC}                 未使用のDockerリソースを削除"
    echo
    echo -e "${BOLD}${WHITE}サービス:${NC}"
    echo -e "  ${YELLOW}all${NC}         全てのサービス ${DIM}(デフォルト)${NC}"
    echo -e "  ${YELLOW}bot${NC}         Discord Bot"
    echo -e "  ${YELLOW}api${NC}         APIサーバー"
    echo -e "  ${YELLOW}web${NC}         Webダッシュボード"
    echo -e "  ${YELLOW}db${NC}          PostgreSQLデータベース"
    echo
    echo -e "${BOLD}${WHITE}例:${NC}"
    echo -e "  ${DIM}shardbot start${NC}             全サービスを起動"
    echo -e "  ${DIM}shardbot stop bot${NC}          Botのみ停止"
    echo -e "  ${DIM}shardbot status api${NC}        APIの状態を確認"
    echo -e "  ${DIM}shardbot logs web 100${NC}      Webダッシュボードの最新100行"
    echo -e "  ${DIM}shardbot deploy${NC}            全サービスをデプロイ"
    echo -e "  ${DIM}shardbot update${NC}            コードを更新して再デプロイ"
}

# Docker権限チェック関数
check_docker_permission() {
    # Dockerソケットへのアクセス権限をチェック
    if docker info &>/dev/null; then
        return 0 # 権限あり
    else
        return 1 # 権限なし
    fi
}

# Docker Compose コマンドの実行関数
run_docker_compose() {
    if check_docker_permission; then
        # 権限があれば通常実行
        docker-compose "$@"
    else
        # 権限がなければsudoで実行、パスワード入力を求める
        echo -e "${YELLOW}Dockerへのアクセス権限がありません。sudo権限が必要です...${NC}"
        echo -e "${DIM}注意: 頻繁にsudoが必要な場合は、ユーザーをdockerグループに追加してください:${NC}"
        echo -e "${DIM}   sudo usermod -aG docker $USER${NC}"
        echo -e "${DIM}   (変更を反映するにはログアウト後、再ログインしてください)${NC}"
        echo
        sudo docker-compose "$@"
    fi
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

# デプロイメント - ビルドして起動
deploy_services() {
    echo -e "${BLUE}全サービスをデプロイしています...${NC}"
    
    # コンテナをビルド
    echo -e "${YELLOW}コンテナをビルドしています...${NC}"
    run_docker_compose build
    
    # コンテナを起動
    echo -e "${GREEN}コンテナを起動しています...${NC}"
    run_docker_compose up -d
    
    # 状態を表示
    echo -e "${BLUE}デプロイ後の状態:${NC}"
    run_docker_compose ps
    
    echo -e "${GREEN}デプロイが完了しました${NC}"
}

# 更新機能 - リポジトリの更新から再デプロイまで
update_services() {
    echo -e "${BLUE}ShardBotを更新しています...${NC}"
    
    # サービスを停止
    echo -e "${YELLOW}サービスを停止しています...${NC}"
    run_docker_compose down
    
    # Gitプロジェクトの場合はコードを更新
    if [ -d "$PROJECT_DIR/.git" ]; then
        echo -e "${YELLOW}コードを更新しています...${NC}"
        git pull
    else
        echo -e "${YELLOW}Gitリポジトリが見つかりません。コードの更新をスキップします。${NC}"
    fi
    
    # 依存関係を更新
    echo -e "${YELLOW}依存関係を更新しています...${NC}"
    if [ -f "$PROJECT_DIR/bot/src/requirements.txt" ]; then
        echo -e "${DIM}Botの依存関係を更新中...${NC}"
        # ここでは実際にインストールせず、Dockerビルド時に行う
    fi
    
    if [ -f "$PROJECT_DIR/web/client/package.json" ]; then
        echo -e "${DIM}Webクライアントの依存関係を更新中...${NC}"
        # ここでは実際にインストールせず、Dockerビルド時に行う
    fi
    
    # 再デプロイ
    deploy_services
}

# 環境と設定のチェック
check_environment() {
    echo -e "${BLUE}環境と設定をチェックしています...${NC}"
    
    # .envファイルの存在確認
    if [ -f "$PROJECT_DIR/.env" ]; then
        echo -e "${GREEN}✓ .envファイルが存在します${NC}"
        
        # 必須環境変数のチェック
        ENV_MISSING=0
        
        # 環境変数をチェック
        if grep -q "DISCORD_TOKEN" "$PROJECT_DIR/.env"; then
            echo -e "${GREEN}✓ DISCORD_TOKEN が設定されています${NC}"
        else
            echo -e "${RED}✗ DISCORD_TOKEN が設定されていません${NC}"
            ENV_MISSING=1
        fi
        
        if grep -q "DB_USER" "$PROJECT_DIR/.env" && grep -q "DB_PASSWORD" "$PROJECT_DIR/.env" && grep -q "DB_NAME" "$PROJECT_DIR/.env"; then
            echo -e "${GREEN}✓ データベース設定が存在します${NC}"
        else
            echo -e "${RED}✗ データベース設定が不完全です${NC}"
            ENV_MISSING=1
        fi
        
        # 環境変数の問題があれば指示を表示
        if [ $ENV_MISSING -eq 1 ]; then
            echo -e "${YELLOW}環境変数の設定に問題があります。config/example.envを参考に.envファイルを更新してください。${NC}"
        fi
    else
        echo -e "${RED}✗ .envファイルが見つかりません${NC}"
        echo -e "${YELLOW}config/example.envを.envにコピーし、必要な環境変数を設定してください。${NC}"
    fi
    
    # Dockerの状態確認
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Dockerがインストールされています${NC}"
        
        # Dockerサービスの状態を確認
        if systemctl is-active --quiet docker; then
            echo -e "${GREEN}✓ Dockerサービスが実行中です${NC}"
        else
            echo -e "${RED}✗ Dockerサービスが停止しています${NC}"
            echo -e "${YELLOW}Dockerサービスを開始してください: sudo systemctl start docker${NC}"
        fi
        
        # Docker Composeの確認
        if command -v docker-compose &> /dev/null; then
            echo -e "${GREEN}✓ Docker Composeがインストールされています${NC}"
        else
            echo -e "${RED}✗ Docker Composeがインストールされていません${NC}"
            echo -e "${YELLOW}Docker Composeをインストールしてください${NC}"
        fi
    else
        echo -e "${RED}✗ Dockerがインストールされていません${NC}"
        echo -e "${YELLOW}Dockerをインストールしてください${NC}"
    fi
    
    # ディレクトリ構造のチェック
    echo -e "${BLUE}ディレクトリ構造をチェックしています...${NC}"
    STRUCTURE_ISSUES=0
    
    if [ -d "$PROJECT_DIR/bot" ] && [ -f "$PROJECT_DIR/bot/Dockerfile" ]; then
        echo -e "${GREEN}✓ Botのディレクトリ構造は正常です${NC}"
    else
        echo -e "${RED}✗ Botのディレクトリ構造に問題があります${NC}"
        STRUCTURE_ISSUES=1
    fi
    
    if [ -d "$PROJECT_DIR/web" ]; then
        echo -e "${GREEN}✓ Webディレクトリが存在します${NC}"
    else
        echo -e "${YELLOW}! Webディレクトリが見つかりません${NC}"
        STRUCTURE_ISSUES=1
    fi
    
    if [ $STRUCTURE_ISSUES -eq 1 ]; then
        echo -e "${YELLOW}ディレクトリ構造に問題があります。リポジトリを再クローンするか、ファイルを復元してください。${NC}"
    fi
}

# 未使用のDockerリソースの削除
prune_resources() {
    echo -e "${BLUE}未使用のDockerリソースを削除しています...${NC}"
    
    # 確認
    read -p "未使用のDockerリソース（コンテナ、イメージ、ボリューム、ネットワーク）を削除しますか？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}未使用のコンテナを削除しています...${NC}"
        if check_docker_permission; then
            docker container prune -f
        else
            sudo docker container prune -f
        fi
        
        echo -e "${YELLOW}未使用のイメージを削除しています...${NC}"
        if check_docker_permission; then
            docker image prune -f
        else
            sudo docker image prune -f
        fi
        
        echo -e "${YELLOW}未使用のボリュームを削除しています...${NC}"
        if check_docker_permission; then
            docker volume prune -f
        else
            sudo docker volume prune -f
        fi
        
        echo -e "${YELLOW}未使用のネットワークを削除しています...${NC}"
        if check_docker_permission; then
            docker network prune -f
        else
            sudo docker network prune -f
        fi
        
        echo -e "${GREEN}未使用のDockerリソースを削除しました${NC}"
    else
        echo -e "${YELLOW}操作をキャンセルしました${NC}"
    fi
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
    deploy)
        deploy_services
        ;;
    update)
        update_services
        ;;
    check)
        check_environment
        ;;
    prune)
        prune_resources
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