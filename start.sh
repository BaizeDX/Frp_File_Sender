#!/bin/bash

# FileP2P 启动脚本

echo "========================================="
echo "  🚀 FileP2P - 大文件点对点传输工具"
echo "========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

# 检查并安装依赖
echo "📦 检查依赖..."
pip3 install -r requirements.txt -q

# 创建必要的目录
mkdir -p files logs temp

# 复制frp配置模板（如果不存在）
if [ ! -f "config/frpc.ini" ]; then
    cp config/frpc_template.ini config/frpc.ini
    echo "⚙️  已创建frp配置文件: config/frpc.ini"
    echo "   请编辑配置文件填入你的frp服务器信息"
fi

# 启动服务器
echo ""
echo "🌐 启动服务器..."
echo "   本地地址: http://localhost:8848"
echo "   共享目录: $(pwd)/files"
echo ""

python3 -m server.main "$@"