#!/bin/bash
# fnos-git-auth 一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.sh | bash
# 或者: wget -qO- https://raw.githubusercontent.com/donnel666/fnos-git-auth/main/scripts/install.sh | bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
REPO="donnel666/fnos-git-auth"
INSTALL_DIR="${FNOS_GIT_AUTH_DIR:-$HOME/.fnos-git-auth}"
BIN_DIR="${FNOS_GIT_AUTH_BIN:-$HOME/.local/bin}"

echo -e "${BLUE}fnos-git-auth 安装脚本${NC}"
echo "=================================="

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        Linux*)  OS="linux";;
        Darwin*) OS="macos";;
        MINGW*|MSYS*|CYGWIN*) OS="windows";;
        *)       OS="unknown";;
    esac
    echo -e "${GREEN}检测到操作系统: ${OS}${NC}"
}

# 检测架构
detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64) ARCH="x64";;
        aarch64|arm64) ARCH="arm64";;
        armv7l) ARCH="armv7";;
        i386|i686) ARCH="x86";;
        *) ARCH="unknown";;
    esac
    echo -e "${GREEN}检测到架构: ${ARCH}${NC}"
}

# 获取最新版本
get_latest_version() {
    if command -v curl &> /dev/null; then
        VERSION=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    elif command -v wget &> /dev/null; then
        VERSION=$(wget -qO- "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    else
        echo -e "${RED}错误: 需要 curl 或 wget${NC}"
        exit 1
    fi
    
    if [ -z "$VERSION" ]; then
        echo -e "${YELLOW}警告: 无法获取最新版本，使用默认版本 v0.1.0${NC}"
        VERSION="v0.1.0"
    fi
    echo -e "${GREEN}最新版本: ${VERSION}${NC}"
}

# 构建下载 URL
build_download_url() {
    case "$OS" in
        linux)
            if [ "$ARCH" = "x64" ]; then
                FILENAME="fnos-git-auth-linux-x86_64"
            elif [ "$ARCH" = "arm64" ]; then
                FILENAME="fnos-git-auth-linux-arm64"
            else
                echo -e "${RED}错误: 不支持的架构 ${ARCH}${NC}"
                exit 1
            fi
            ;;
        macos)
            if [ "$ARCH" = "x64" ]; then
                FILENAME="fnos-git-auth-macos-x64"
            elif [ "$ARCH" = "arm64" ]; then
                FILENAME="fnos-git-auth-macos-arm64"
            else
                echo -e "${RED}错误: 不支持的架构 ${ARCH}${NC}"
                exit 1
            fi
            ;;
        windows)
            FILENAME="fnos-git-auth-windows-x64.exe"
            ;;
        *)
            echo -e "${RED}错误: 不支持的操作系统 ${OS}${NC}"
            exit 1
            ;;
    esac
    
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${FILENAME}"
    echo -e "${GREEN}下载地址: ${DOWNLOAD_URL}${NC}"
}

# 下载文件
download_file() {
    echo -e "${BLUE}正在下载...${NC}"
    
    # 创建安装目录
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    TARGET_FILE="$BIN_DIR/fnos-git-auth"
    if [ "$OS" = "windows" ]; then
        TARGET_FILE="$BIN_DIR/fnos-git-auth.exe"
    fi
    
    if command -v curl &> /dev/null; then
        curl -fsSL "$DOWNLOAD_URL" -o "$TARGET_FILE"
    elif command -v wget &> /dev/null; then
        wget -qO "$TARGET_FILE" "$DOWNLOAD_URL"
    fi
    
    # 添加执行权限
    if [ "$OS" != "windows" ]; then
        chmod +x "$TARGET_FILE"
    fi
    
    echo -e "${GREEN}已下载到: ${TARGET_FILE}${NC}"
}

# 配置 PATH
setup_path() {
    # 检查是否已在 PATH 中
    if echo "$PATH" | grep -q "$BIN_DIR"; then
        echo -e "${GREEN}$BIN_DIR 已在 PATH 中${NC}"
        return
    fi
    
    # 检测 shell 并添加到配置文件
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            RC_FILE="$HOME/.bashrc"
            ;;
        zsh)
            RC_FILE="$HOME/.zshrc"
            ;;
        fish)
            RC_FILE="$HOME/.config/fish/config.fish"
            ;;
        *)
            RC_FILE=""
            ;;
    esac
    
    if [ -n "$RC_FILE" ]; then
        echo "" >> "$RC_FILE"
        echo "# fnos-git-auth" >> "$RC_FILE"
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$RC_FILE"
        echo -e "${GREEN}已添加 $BIN_DIR 到 $RC_FILE${NC}"
        echo -e "${YELLOW}请运行 'source $RC_FILE' 或重新打开终端使配置生效${NC}"
    else
        echo -e "${YELLOW}请手动将 $BIN_DIR 添加到 PATH${NC}"
    fi
}

# 验证安装
verify_installation() {
    echo -e "${BLUE}验证安装...${NC}"
    
    TARGET_FILE="$BIN_DIR/fnos-git-auth"
    if [ "$OS" = "windows" ]; then
        TARGET_FILE="$BIN_DIR/fnos-git-auth.exe"
    fi
    
    if [ -f "$TARGET_FILE" ]; then
        echo -e "${GREEN}安装成功!${NC}"
        echo ""
        echo "使用方法:"
        echo "  fnos-git-auth --help     # 查看帮助"
        echo "  fnos-git-auth login      # 登录"
        echo "  fnos-git-auth status     # 查看状态"
        echo ""
        
        # 尝试运行
        if "$TARGET_FILE" --version &> /dev/null; then
            VERSION_INFO=$("$TARGET_FILE" --version 2>&1 || true)
            echo -e "${GREEN}版本信息: ${VERSION_INFO}${NC}"
        fi
    else
        echo -e "${RED}安装失败: 文件未找到${NC}"
        exit 1
    fi
}

# 卸载函数
uninstall() {
    echo -e "${YELLOW}正在卸载 fnos-git-auth...${NC}"
    
    TARGET_FILE="$BIN_DIR/fnos-git-auth"
    if [ -f "$TARGET_FILE" ]; then
        rm -f "$TARGET_FILE"
        echo -e "${GREEN}已删除 $TARGET_FILE${NC}"
    fi
    
    if [ -f "$TARGET_FILE.exe" ]; then
        rm -f "$TARGET_FILE.exe"
        echo -e "${GREEN}已删除 $TARGET_FILE.exe${NC}"
    fi
    
    if [ -d "$INSTALL_DIR" ]; then
        read -p "是否删除配置目录 $INSTALL_DIR? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            echo -e "${GREEN}已删除 $INSTALL_DIR${NC}"
        fi
    fi
    
    echo -e "${GREEN}卸载完成${NC}"
}

# 主函数
main() {
    # 检查是否是卸载
    if [ "$1" = "uninstall" ] || [ "$1" = "--uninstall" ]; then
        uninstall
        exit 0
    fi
    
    detect_os
    detect_arch
    get_latest_version
    build_download_url
    download_file
    setup_path
    verify_installation
}

main "$@"
