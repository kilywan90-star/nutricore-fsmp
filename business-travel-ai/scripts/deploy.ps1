# 差序MVP 部署脚本 (Windows PowerShell)
# 用法: .\scripts\deploy.ps1 -Remote "root@server-ip"
#
# 参数:
#   -Remote     SSH连接地址，如 root@1.2.3.4
#   -Port       服务端口 (默认 3000)

param(
    [Parameter(Mandatory=$true)]
    [string]$Remote,
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$AppName = "business-travel-ai"

Write-Host "=== 差序MVP 部署 ===" -ForegroundColor Cyan
Write-Host "目标: $Remote"
Write-Host "项目: $ProjectDir"

# ============================================================
# 1. 本地构建
# ============================================================
Write-Host "`n[1/5] 本地生产构建..." -ForegroundColor Yellow
Set-Location $ProjectDir
npm run build
if ($LASTEXITCODE -ne 0) { throw "构建失败" }

# ============================================================
# 2. 打包
# ============================================================
Write-Host "[2/5] 打包项目文件..." -ForegroundColor Yellow
$Tarball = "$env:TEMP\business-travel-ai-deploy.tar.gz"

tar czf $Tarball `
    --exclude="node_modules" `
    --exclude=".next" `
    --exclude="data\*.db" `
    --exclude="data\*.db-shm" `
    --exclude="data\*.db-wal" `
    --exclude=".env" `
    --exclude=".env.local" `
    --exclude=".git" `
    --exclude="*.tsbuildinfo" `
    --exclude="scripts\deploy.ps1" `
    -C (Split-Path -Parent $ProjectDir) `
    (Split-Path -Leaf $ProjectDir)

if ($LASTEXITCODE -ne 0) { throw "打包失败" }
$Size = [math]::Round((Get-Item $Tarball).Length / 1MB, 1)
Write-Host "  包大小: ${Size}MB"

# ============================================================
# 3. 传输到服务器
# ============================================================
Write-Host "[3/5] 传输到服务器..." -ForegroundColor Yellow
scp $Tarball "${Remote}:/tmp/business-travel-ai-deploy.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "传输失败" }
Remove-Item $Tarball -Force

# ============================================================
# 4. 服务器端操作
# ============================================================
Write-Host "[4/5] 服务器端解压 + 安装依赖..." -ForegroundColor Yellow

# 写入远程脚本到临时文件 (单引号heredoc防止PowerShell展开bash变量)
$RemoteScriptFile = "$env:TEMP\remote-deploy.sh"
@'
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

# 清理旧文件
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

# 安装依赖
echo "  安装依赖..."
npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# 初始化数据库 (如果没有)
if [ ! -f "$APP_DIR/data/travel.db" ]; then
  echo "  初始化数据库 + 导入种子数据..."
  npx tsx src/db/seed.ts
else
  echo "  数据库已存在，跳过种子导入"
fi

# 构建 (如果.next不存在则在服务器端构建)
if [ ! -d "$APP_DIR/.next" ]; then
  echo "  服务器端构建..."
  npm install typescript --save-dev 2>/dev/null
  npx next build
fi

# 停止旧进程
pm2 delete business-travel-ai 2>/dev/null || true

# 启动
echo "  启动服务..."
PORT=__PORT__ pm2 start "npm start" --name business-travel-ai --cwd "$APP_DIR" --max-memory-restart 512M
pm2 save

echo ""
echo "=== 部署完成 ==="
pm2 status
'@ -replace '__PORT__', $Port | Set-Content -Path $RemoteScriptFile -Encoding UTF8 -NoNewline

scp $RemoteScriptFile "${Remote}:/tmp/remote-deploy.sh"
ssh $Remote "bash /tmp/remote-deploy.sh"
Remove-Item $RemoteScriptFile -Force
if ($LASTEXITCODE -ne 0) { throw "服务器端操作失败" }

# ============================================================
# 5. 验证
# ============================================================
Write-Host "`n[5/5] 验证服务..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
$HealthResult = ssh $Remote "curl -s http://localhost:$Port/api/health"
Write-Host "  健康检查: $HealthResult"

# 提取服务器IP
$ServerHost = ($Remote -split '@')[-1]

Write-Host "`n=== 部署成功 ===" -ForegroundColor Green
Write-Host "访问: http://${ServerHost}:${Port}" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:"
Write-Host "  查看日志: ssh $Remote 'pm2 logs $AppName'"
Write-Host "  重启服务: ssh $Remote 'pm2 restart $AppName'"
Write-Host "  查看状态: ssh $Remote 'pm2 status'"
