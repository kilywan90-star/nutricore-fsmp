#!/bin/bash
# 差序MVP 部署脚本 — 在本地执行
# 用法: bash scripts/deploy.sh user@server-ip
#
# 环境变量 (可选):
#   DASHSCOPE_API_KEY  - DashScope API Key (不设置则LLM功能禁用，regex降级可用)
#   PORT               - 服务端口 (默认 3000)

set -euo pipefail

# ============================================================
# 配置
# ============================================================
REMOTE="${1:?用法: bash deploy.sh user@server-ip}"
APP_DIR="/opt/business-travel-ai"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== 差序MVP 部署 ==="
echo "目标: $REMOTE"
echo "项目: $PROJECT_DIR"

# ============================================================
# 1. 本地构建 (在本地编译，减少服务器CPU压力)
# ============================================================
echo ""
echo "[1/5] 本地生产构建..."
cd "$PROJECT_DIR"
npm run build

# ============================================================
# 2. 打包 (排除不需要的文件)
# ============================================================
echo "[2/5] 打包项目文件..."
TARBALL="/tmp/business-travel-ai-deploy.tar.gz"
tar czf "$TARBALL" \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='data/*.db' \
  --exclude='data/*.db-shm' \
  --exclude='data/*.db-wal' \
  --exclude='.env' \
  --exclude='.env.local' \
  --exclude='.git' \
  --exclude='*.tsbuildinfo' \
  --exclude='scripts/deploy.sh' \
  -C "$(dirname "$PROJECT_DIR")" \
  "$(basename "$PROJECT_DIR")"

SIZE=$(du -h "$TARBALL" | cut -f1)
echo "  包大小: $SIZE"

# ============================================================
# 3. 传输到服务器
# ============================================================
echo "[3/5] 传输到服务器..."
scp "$TARBALL" "$REMOTE:/tmp/business-travel-ai-deploy.tar.gz"
rm -f "$TARBALL"

# ============================================================
# 4. 服务器端操作
# ============================================================
echo "[4/5] 服务器端解压 + 安装依赖..."
ssh "$REMOTE" bash -s <<'REMOTE_SCRIPT'
set -euo pipefail
APP_DIR="/opt/business-travel-ai"

# 解压
echo "  解压..."
tar xzf /tmp/business-travel-ai-deploy.tar.gz -C /tmp/
# 保留现有数据库
if [ -f "$APP_DIR/data/travel.db" ]; then
  echo "  保留现有数据库"
  cp "$APP_DIR/data/travel.db" /tmp/_keep_travel.db
fi
# 清理旧文件 (保留data目录)
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
# 移动新文件
cp -r /tmp/business-travel-ai/* "$APP_DIR/"
rm -rf /tmp/business-travel-ai /tmp/business-travel-ai-deploy.tar.gz
# 恢复数据库
if [ -f /tmp/_keep_travel.db ]; then
  mkdir -p "$APP_DIR/data"
  mv /tmp/_keep_travel.db "$APP_DIR/data/travel.db"
fi

cd "$APP_DIR"

# 安装依赖 (仅生产依赖)
echo "  安装依赖..."
npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# 如果没有数据库，运行种子脚本
if [ ! -f "$APP_DIR/data/travel.db" ]; then
  echo "  初始化数据库 + 导入种子数据..."
  npx tsx src/db/seed.ts
else
  echo "  数据库已存在，跳过种子导入"
fi

# 停止旧进程
pm2 delete business-travel-ai 2>/dev/null || true

# 启动新进程
echo "  启动服务..."
pm2 start "npm start" \
  --name business-travel-ai \
  --cwd "$APP_DIR" \
  --max-memory-restart 512M

pm2 save

echo ""
echo "=== 部署完成 ==="
pm2 status
REMOTE_SCRIPT

# ============================================================
# 5. 验证
# ============================================================
echo ""
echo "[5/5] 验证服务..."
sleep 3
ssh "$REMOTE" 'curl -s http://localhost:3000/api/health'

echo ""
echo ""
echo "=== 部署成功 ==="
echo "访问: http://$(echo "$REMOTE" | sed 's/.*@//'):3000"
echo ""
echo "常用命令:"
echo "  查看日志: ssh $REMOTE 'pm2 logs business-travel-ai'"
echo "  重启服务: ssh $REMOTE 'pm2 restart business-travel-ai'"
echo "  查看状态: ssh $REMOTE 'pm2 status'"
