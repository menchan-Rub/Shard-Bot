#!/bin/bash

# 色の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# 現在のディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

echo -e "${BOLD}${BLUE}Shard Bot インストールスクリプト${NC}"
echo -e "このスクリプトはShardBot管理ツールをシステム全体で使用できるようにインストールします。"
echo

# 設定ファイルのパス修正
echo -e "${YELLOW}スクリプトファイルを更新しています...${NC}"
TMP_FILE=$(mktemp)
sed "s|PROJECT_DIR=\"/home/menchan/Programming/Discord/Shard-Bot\"|PROJECT_DIR=\"$PROJECT_DIR\"|g" "$SCRIPT_DIR/shardbot.sh" > "$TMP_FILE"
mv "$TMP_FILE" "$SCRIPT_DIR/shardbot.sh"
chmod +x "$SCRIPT_DIR/shardbot.sh"
echo -e "${GREEN}✓ スクリプトのパスを更新しました${NC}"

# dockerグループの存在確認
if getent group docker >/dev/null; then
  # dockerグループにユーザーを追加するか確認
  echo -e "${YELLOW}Dockerの権限設定${NC}"
  if groups "$USER" | grep -q 'docker'; then
    echo -e "${GREEN}✓ ユーザー '$USER' はすでにdockerグループに所属しています${NC}"
  else
    echo -e "Dockerコマンドを実行するには、通常sudoが必要です。"
    echo -e "sudoなしでDockerを使用するには、ユーザーをdockerグループに追加する必要があります。"
    read -p "ユーザー '$USER' をdockerグループに追加しますか？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}dockerグループにユーザーを追加するには管理者権限が必要です...${NC}"
        sudo usermod -aG docker "$USER"
      else
        usermod -aG docker "$USER"
      fi
      echo -e "${GREEN}✓ ユーザー '$USER' をdockerグループに追加しました${NC}"
      echo -e "${YELLOW}注意: この変更を反映するには、ログアウト後に再ログインしてください${NC}"
    else
      echo -e "${YELLOW}ユーザーをdockerグループに追加しませんでした。${NC}"
      echo -e "${YELLOW}Dockerコマンドを実行する際にsudoの入力が求められる場合があります。${NC}"
    fi
  fi
fi

# ユーザー権限の確認
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}管理者権限が必要です。sudoを使用します...${NC}"
  
  # 管理スクリプトのインストール
  echo -e "${BLUE}Shard Bot管理スクリプトをインストールしています...${NC}"
  sudo cp "$SCRIPT_DIR/shardbot.sh" /usr/local/bin/shardbot
  sudo chmod +x /usr/local/bin/shardbot
  echo -e "${GREEN}✓ /usr/local/bin/shardbot にインストールしました${NC}"
  
  # Bash補完のインストール
  echo -e "${BLUE}Bash補完をインストールしています...${NC}"
  if [ -d "/etc/bash_completion.d" ]; then
    sudo cp "$SCRIPT_DIR/shardbot-completion.bash" /etc/bash_completion.d/shardbot
    echo -e "${GREEN}✓ Bash補完をインストールしました${NC}"
  else
    echo -e "${YELLOW}警告: bash_completion.dディレクトリが見つかりません。補完は手動でインストールしてください。${NC}"
    echo -e "以下のコマンドをあなたの~/.bashrcに追加してください:"
    echo -e "${BLUE}source $SCRIPT_DIR/shardbot-completion.bash${NC}"
  fi
  
  echo
  echo -e "${GREEN}${BOLD}インストールが完了しました!${NC}"
  echo -e "どのディレクトリからでも '${BOLD}shardbot${NC}' コマンドを使用できます。"
  echo -e "補完機能を有効にするには、ターミナルを再起動するか '${BLUE}source ~/.bashrc${NC}' を実行してください。"
else
  # すでに管理者権限がある場合
  echo -e "${BLUE}Shard Bot管理スクリプトをインストールしています...${NC}"
  cp "$SCRIPT_DIR/shardbot.sh" /usr/local/bin/shardbot
  chmod +x /usr/local/bin/shardbot
  echo -e "${GREEN}✓ /usr/local/bin/shardbot にインストールしました${NC}"
  
  echo -e "${BLUE}Bash補完をインストールしています...${NC}"
  if [ -d "/etc/bash_completion.d" ]; then
    cp "$SCRIPT_DIR/shardbot-completion.bash" /etc/bash_completion.d/shardbot
    echo -e "${GREEN}✓ Bash補完をインストールしました${NC}"
  else
    echo -e "${YELLOW}警告: bash_completion.dディレクトリが見つかりません。補完は手動でインストールしてください。${NC}"
    echo -e "以下のコマンドをあなたの~/.bashrcに追加してください:"
    echo -e "${BLUE}source $SCRIPT_DIR/shardbot-completion.bash${NC}"
  fi
  
  echo
  echo -e "${GREEN}${BOLD}インストールが完了しました!${NC}"
  echo -e "どのディレクトリからでも '${BOLD}shardbot${NC}' コマンドを使用できます。"
  echo -e "補完機能を有効にするには、ターミナルを再起動するか '${BLUE}source ~/.bashrc${NC}' を実行してください。"
fi 