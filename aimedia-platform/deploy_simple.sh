#!/bin/bash
# ============================================
# 轻量部署 (无 Docker，直接运行)
# 适用: 单台云服务器 (CentOS/Ubuntu)
# 用法: bash deploy_simple.sh
# ============================================
set -e

APP_DIR="/opt/aimedia-platform"
PYTHON_BIN="python3.12"

echo "=== AI Media Platform - Simple Deploy ==="

# 1. 安装系统依赖
echo "[1/6] Installing system packages ..."
if command -v apt >/dev/null 2>&1; then
    sudo apt update -qq
    sudo apt install -y -qq python3.12 python3.12-venv nginx postgresql redis
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y python3.12 nginx postgresql redis
fi

# 2. 创建目录
echo "[2/6] Creating directories ..."
sudo mkdir -p $APP_DIR /data/storage
sudo chown -R $USER:$USER $APP_DIR /data/storage

# 3. 复制项目
echo "[3/6] Copying project ..."
cp -r backend frontend requirements-freeze.txt $APP_DIR/

# 4. 安装 Python 依赖
echo "[4/6] Installing Python dependencies ..."
cd $APP_DIR
$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install -r backend/requirements-freeze.txt

# 5. 初始化数据库
echo "[5/6] Initializing database ..."
# PostgreSQL setup
sudo -u postgres psql -c "CREATE USER aimedia WITH PASSWORD 'aimedia123';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE aimedia OWNER aimedia;" 2>/dev/null || true

cd backend
alembic upgrade head
python -m app.core.seed
cd ..

# 6. 配置 Nginx + systemd
echo "[6/6] Configuring Nginx & systemd ..."
sudo cp nginx.conf /etc/nginx/conf.d/aimedia.conf
sudo cp frontend/dist /usr/share/nginx/html/aimedia -r

sudo tee /etc/systemd/system/aimedia.service > /dev/null << EOF
[Unit]
Description=AI Media Platform Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now aimedia nginx redis postgresql

echo ""
echo "=== Deploy complete ==="
echo "  Access: http://<server-ip>"
echo "  Login:  admin / admin123"
echo "  Status: sudo systemctl status aimedia nginx"
