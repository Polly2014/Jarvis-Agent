#!/bin/bash
# Jarvis Daemon 卸载脚本

PLIST_NAME="com.polly.jarvis.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🛑 卸载 Jarvis Daemon..."

# 停止服务
if launchctl list | grep -q "com.polly.jarvis"; then
    echo "   停止服务..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# 删除 plist 文件
if [ -f "$PLIST_PATH" ]; then
    echo "   删除配置文件..."
    rm "$PLIST_PATH"
fi

echo "✅ Jarvis Daemon 已卸载"
echo ""
echo "注意: ~/.jarvis 目录保留（包含记忆和发现）"
echo "如需完全清除，请手动删除: rm -rf ~/.jarvis"
