#!/bin/bash
# ============================================
# AI融媒体平台 - 云服务器部署脚本
# 用法: bash deploy.sh
# ============================================
set -e

echo "============================================"
echo "  AI Media Platform - Cloud Deploy"
echo "============================================"

# ── 1. 检查环境 ──
echo "[1/5] Checking environment ..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not installed"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose not installed"; exit 1; }
echo "  Docker OK"

# ── 2. 配置 ──
echo "[2/5] Setting up config ..."
if [ ! -f .env.production ]; then
    cp .env.production.example .env.production 2>/dev/null || true
    echo "  WARN: Please edit .env.production with your settings"
    echo "  Required: JWT_SECRET_KEY, LLM_API_KEY, DB_PASSWORD"
fi
echo "  Config OK"

# ── 3. 构建前端 ──
echo "[3/5] Building frontend ..."
cd frontend
if [ ! -d node_modules ]; then
    npm install --registry https://registry.npmmirror.com
fi
npm run build
cd ..
echo "  Frontend built: frontend/dist/"

# ── 4. 构建镜像 ──
echo "[4/5] Building Docker images ..."
docker compose -f docker-compose.prod.yml build
echo "  Images built"

# ── 5. 启动 ──
echo "[5/5] Starting services ..."
docker compose -f docker-compose.prod.yml up -d
echo ""

echo "============================================"
echo "  Deploy complete!"
echo "  Check: docker compose -f docker-compose.prod.yml ps"
echo "  Logs:  docker compose -f docker-compose.prod.yml logs -f"
echo "============================================"
