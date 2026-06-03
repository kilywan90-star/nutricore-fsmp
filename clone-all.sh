#!/bin/bash
# ============================================================
# 一键克隆全部项目
# 用法: bash clone-all.sh [目标目录, 默认 ~/claude]
# ============================================================
set -e

TARGET="${1:-$HOME/claude}"
mkdir -p "$TARGET" && cd "$TARGET"
echo "克隆到: $TARGET"
echo ""

# ============================================================
# Step 1: GitHub 连通性检查
# ============================================================
echo "[1/3] 检查 SSH 密钥..."
if ssh -T -o StrictHostKeyChecking=accept-new git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "  SSH 认证 OK"
else
    echo "  [ERROR] SSH 未配置。请先执行:"
    echo "    ssh-keygen -t ed25519 -C \"you@email.com\""
    echo "    cat ~/.ssh/id_ed25519.pub  # 复制到 https://github.com/settings/keys"
    exit 1
fi

# ============================================================
# Step 2: Git 用户配置
# ============================================================
echo ""
echo "[2/3] 配置 Git 用户..."

if [ -z "$(git config --global user.name 2>/dev/null)" ]; then
    git config --global user.name "DDD Developer"
    echo "  git config user.name = DDD Developer"
else
    echo "  git config user.name 已设置: $(git config --global user.name)"
fi

if [ -z "$(git config --global user.email 2>/dev/null)" ]; then
    git config --global user.email "developer@ddd.health"
    echo "  git config user.email = developer@ddd.health"
else
    echo "  git config user.email 已设置: $(git config --global user.email)"
fi

# ============================================================
# Step 3: 克隆全部项目
# ============================================================
echo ""
echo "[3/3] 克隆项目..."

REPOS=(
    "git@github.com:kilywan90-star/h-discovery.git"
    "git@github.com:kilywan90-star/digital-doctor.git"
    "git@github.com:kilywan90-star/seedance-pipeline.git"
    "git@github.com:kilywan90-star/aimedia-platform.git"
    "git@github.com:kilywan90-star/ultrasound-report-mvp.git"
    "git@github.com:kilywan90-star/nutricore-fsmp.git"
)

for repo in "${REPOS[@]}"; do
    name=$(basename "$repo" .git)
    if [ -d "$name" ]; then
        echo "  [SKIP] $name 已存在"
    else
        echo "  [CLONE] $name ..."
        git clone "$repo" 2>&1 | sed 's/^/    /'
    fi
done

# ============================================================
# 完成
# ============================================================
echo ""
echo "======== 全部完成 ========"
echo ""
echo "  cd $TARGET"
echo "  ls -d */"
echo ""
echo "项目分布:"
echo "  超声结构化报告   -> ultrasound-report-mvp"
echo "  审方中心          -> h-discovery"
echo "  AI智能随访         -> digital-doctor"
echo "  自适应视频生成     -> seedance-pipeline"
echo "  一键成片          -> aimedia-platform"
echo "  营养项目(根)       -> nutricore-fsmp"
