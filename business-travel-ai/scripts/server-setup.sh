#!/bin/bash
# 云服务器初始化脚本 — 在服务器上执行一次
# 用法: ssh root@your-server 'bash' < server-setup.sh

set -euo pipefail

echo "=== 差序MVP 服务器初始化 ==="

# 1. 检测系统
if command -v apt-get &>/dev/null; then
  PKG="apt"
elif command -v yum &>/dev/null; then
  PKG="yum"
elif command -v dnf &>/dev/null; then
  PKG="dnf"
else
  echo "ERROR: 不支持的包管理器"
  exit 1
fi
echo "[1/5] 包管理器: $PKG"

# 2. 安装 Node.js 20 LTS (如果没有或版本过低)
install_node() {
  echo "[2/5] 安装 Node.js 20 LTS..."
  if [ "$PKG" = "apt" ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  else
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    $PKG install -y nodejs
  fi
}

if command -v node &>/dev/null; then
  NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)
  if [ "$NODE_VER" -lt 18 ]; then
    echo "Node.js 版本过低 ($(node -v))，需要 >= 18"
    install_node
  else
    echo "[2/5] Node.js $(node -v) 已就绪"
  fi
else
  install_node
fi

# 3. 安装 PM2 (进程管理)
if ! command -v pm2 &>/dev/null; then
  echo "[3/5] 安装 PM2..."
  npm install -g pm2
else
  echo "[3/5] PM2 已就绪"
fi

# 4. 创建应用目录
APP_DIR="/opt/business-travel-ai"
mkdir -p "$APP_DIR"
echo "[4/5] 应用目录: $APP_DIR"

# 5. 创建 data 目录 (持久化数据库)
mkdir -p "$APP_DIR/data"

# 6. 配置防火墙 (如果ufw存在)
if command -v ufw &>/dev/null; then
  ufw allow 3000/tcp 2>/dev/null || true
  echo "[5/5] 防火墙: 已开放 3000 端口"
else
  echo "[5/5] 请确保云服务器安全组已开放 3000 端口"
fi

echo ""
echo "=== 初始化完成 ==="
echo "下一步: 在本地执行 deploy.sh 上传代码并启动服务"
