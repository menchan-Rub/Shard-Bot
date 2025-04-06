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

echo -e "${BOLD}${BLUE}Shard Bot ローカルインストールスクリプト${NC}"
echo -e "このスクリプトはShardBot管理ツールをホームディレクトリにインストールします。"
echo

# ユーザーのbinディレクトリ確認
USER_BIN="$HOME/.local/bin"
if [ ! -d "$USER_BIN" ]; then
  echo -e "${YELLOW}~/.local/binディレクトリが存在しません。作成します...${NC}"
  mkdir -p "$USER_BIN"
fi

# PATHに$USER_BINが含まれているか確認
if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
  echo -e "${YELLOW}警告: $USER_BINがPATHに含まれていません。${NC}"
  echo -e "以下の行を~/.bashrcまたは~/.bash_profileに追加してください:"
  echo -e "${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
  echo
  
  # 追加するか確認
  read -p "今すぐ~/.bashrcに追加しますか？(y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo -e "${GREEN}~/.bashrcに追加しました。変更を有効にするには、ターミナルを再起動するか source ~/.bashrc を実行してください。${NC}"
  fi
fi

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
      echo -e "${YELLOW}dockerグループにユーザーを追加するには管理者権限が必要です...${NC}"
      sudo usermod -aG docker "$USER"
      echo -e "${GREEN}✓ ユーザー '$USER' をdockerグループに追加しました${NC}"
      echo -e "${YELLOW}注意: この変更を反映するには、ログアウト後に再ログインしてください${NC}"
    else
      echo -e "${YELLOW}ユーザーをdockerグループに追加しませんでした。${NC}"
      echo -e "${YELLOW}Dockerコマンドを実行する際にsudoの入力が求められる場合があります。${NC}"
    fi
  fi
fi

# 設定ファイルのパス修正
echo -e "${YELLOW}スクリプトファイルを更新しています...${NC}"
TMP_FILE=$(mktemp)
sed "s|PROJECT_DIR=\"/home/menchan/Programming/Discord/Shard-Bot\"|PROJECT_DIR=\"$PROJECT_DIR\"|g" "$SCRIPT_DIR/shardbot.sh" > "$TMP_FILE"
mv "$TMP_FILE" "$SCRIPT_DIR/shardbot.sh"
chmod +x "$SCRIPT_DIR/shardbot.sh"
echo -e "${GREEN}✓ スクリプトのパスを更新しました${NC}"

# 管理スクリプトのインストール
echo -e "${BLUE}Shard Bot管理スクリプトをインストールしています...${NC}"
cp "$SCRIPT_DIR/shardbot.sh" "$USER_BIN/shardbot"
chmod +x "$USER_BIN/shardbot"
echo -e "${GREEN}✓ $USER_BIN/shardbot にインストールしました${NC}"

# Bash補完のインストール
echo -e "${BLUE}Bash補完を設定しています...${NC}"
COMPLETION_DIR="$HOME/.bash_completion.d"
if [ ! -d "$COMPLETION_DIR" ]; then
  echo -e "${YELLOW}~/.bash_completion.d ディレクトリが存在しません。作成します...${NC}"
  mkdir -p "$COMPLETION_DIR"
fi

# 補完スクリプトのコピー
cp "$SCRIPT_DIR/shardbot-completion.bash" "$COMPLETION_DIR/shardbot"

# .bashrcに補完設定を追加
if ! grep -q "~/.bash_completion.d/shardbot" "$HOME/.bashrc"; then
  echo -e "${YELLOW}補完スクリプトの読み込み設定を.bashrcに追加します...${NC}"
  echo "" >> "$HOME/.bashrc"
  echo "# ShardBot補完" >> "$HOME/.bashrc"
  echo "if [ -f ~/.bash_completion.d/shardbot ]; then" >> "$HOME/.bashrc"
  echo "    . ~/.bash_completion.d/shardbot" >> "$HOME/.bashrc"
  echo "fi" >> "$HOME/.bashrc"
fi

echo -e "${GREEN}✓ Bash補完を設定しました${NC}"

echo
echo -e "${GREEN}${BOLD}インストールが完了しました!${NC}"
echo -e "どのディレクトリからでも '${BOLD}shardbot${NC}' コマンドを使用できます。"
echo -e "補完機能を有効にするには、ターミナルを再起動するか '${BLUE}source ~/.bashrc${NC}' を実行してください。" 