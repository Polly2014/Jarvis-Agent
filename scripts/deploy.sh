#!/bin/bash
# Polly Agent 部署脚本

set -e

echo "🚀 开始部署 Polly Agent..."

# 配置
PROJECT_DIR="/home/polly/Polly-Agent"
SERVICE_NAME="polly-agent"
PYTHON_VERSION="3.11"

# 1. 检查 Python
echo "📦 检查 Python 版本..."
if ! command -v python${PYTHON_VERSION} &> /dev/null; then
    echo "❌ Python ${PYTHON_VERSION} 未安装"
    exit 1
fi

# 2. 进入项目目录
cd "$PROJECT_DIR"

# 3. 安装 Poetry（如果未安装）
if ! command -v poetry &> /dev/null; then
    echo "📦 安装 Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# 4. 安装依赖
echo "📦 安装依赖..."
poetry install --no-dev

# 5. 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，请从 .env.example 复制并配置"
    cp .env.example .env
    echo "请编辑 .env 文件后重新运行部署脚本"
    exit 1
fi

# 6. 创建 systemd 服务文件
echo "📝 创建 systemd 服务文件..."
sudo cp scripts/polly-agent.service /etc/systemd/system/

# 7. 重载 systemd 并启动服务
echo "🔄 重载 systemd 配置..."
sudo systemctl daemon-reload

echo "🚀 启动服务..."
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

# 8. 检查服务状态
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "✅ Polly Agent 部署成功！"
    echo ""
    echo "📊 服务状态:"
    sudo systemctl status ${SERVICE_NAME} --no-pager
    echo ""
    echo "📝 查看日志: journalctl -u ${SERVICE_NAME} -f"
else
    echo "❌ 服务启动失败，请检查日志:"
    journalctl -u ${SERVICE_NAME} -n 20
    exit 1
fi
