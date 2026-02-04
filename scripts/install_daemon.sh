#!/bin/bash
# Jarvis Daemon 安装脚本
# 用于设置 launchd 开机自启

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.polly.jarvis.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
JARVIS_HOME="$HOME/.jarvis"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               🫀 Jarvis Daemon 安装脚本                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 创建 Jarvis 家目录
echo "📁 创建 Jarvis 家目录..."
mkdir -p "$JARVIS_HOME"/{logs,memory,skills}

# 检查 plist 文件
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ 错误: 找不到 $PLIST_SOURCE"
    exit 1
fi

# 停止已有的服务
if launchctl list | grep -q "com.polly.jarvis"; then
    echo "🛑 停止已有的 Jarvis 服务..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# 复制 plist 文件
echo "📋 安装 launchd 配置..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# 更新 plist 中的路径
echo "🔧 更新配置中的路径..."
sed -i '' "s|/Users/polly|$HOME|g" "$PLIST_DEST"

# 加载服务
echo "🚀 启动 Jarvis 服务..."
launchctl load "$PLIST_DEST"

# 检查状态
sleep 2
if launchctl list | grep -q "com.polly.jarvis"; then
    echo ""
    echo "✅ Jarvis Daemon 安装成功！"
    echo ""
    echo "📊 状态检查:"
    launchctl list | grep "com.polly.jarvis" || echo "   (服务正在启动中...)"
    echo ""
    echo "📋 常用命令:"
    echo "   查看状态:  launchctl list | grep jarvis"
    echo "   查看日志:  tail -f ~/.jarvis/logs/daemon.log"
    echo "   停止服务:  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
    echo "   启动服务:  launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
    echo ""
    echo "🎉 Jarvis 已开始监控你的工作目录！"
else
    echo ""
    echo "⚠️ 服务可能未成功启动，请检查日志:"
    echo "   tail -f ~/.jarvis/logs/daemon.log"
fi
