# 数字医生分身 — 部署实施安装手册

> 版本：v2.0 | 适用：M1+P0+P1+P2+P3 全功能版 | 日期：2026-05-30

---

## 一、部署架构

```
┌──────────────────────────────────────────────────────────┐
│                      医院内网                             │
│                                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │
│  │ Nginx   │  │ Backend │  │ Celery  │  │ Celery    │  │
│  │ :80/443 │─▶│ :8000   │  │ Worker  │  │ Beat      │  │
│  └─────────┘  └────┬────┘  └────┬────┘  └─────┬──────┘  │
│                    │            │              │         │
│              ┌─────┴──────┬─────┴──────────────┘         │
│              ▼            ▼                               │
│        ┌──────────┐ ┌──────────┐                         │
│        │PostgreSQL│ │  Redis   │                         │
│        │   :5432  │ │  :6379   │                         │
│        └──────────┘ └──────────┘                         │
│                                                          │
│  可选监控栈:                                              │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐               │
│  │Prometheus│ │ Grafana  │ │ Exporters  │               │
│  │  :9090   │ │  :3001   │ │            │               │
│  └──────────┘ └──────────┘ └────────────┘               │
└──────────────────────────────────────────────────────────┘
```

---

## 二、服务器要求

### 最低配置（试用/小规模，≤200患者）

| 资源 | 规格 |
|------|------|
| CPU | 4 核 |
| 内存 | 8 GB |
| 磁盘 | 100 GB SSD |
| 操作系统 | Ubuntu 22.04 / CentOS 8 / Debian 12 |
| Docker | 24.0+ |
| Docker Compose | 2.20+ |

### 推荐配置（正式运行，200-2000患者）

| 资源 | 规格 |
|------|------|
| CPU | 8 核 |
| 内存 | 16 GB |
| 磁盘 | 500 GB SSD（含备份空间） |
| 操作系统 | Ubuntu 22.04 LTS |

### 网络要求

| 端口 | 方向 | 协议 | 用途 |
|------|------|------|------|
| 80 | 入站 | HTTP | 前端+API（生产应关闭，仅用于证书申请） |
| 443 | 入站 | HTTPS | 前端+API（生产唯一入口） |
| 5432 | 内部 | TCP | PostgreSQL（不对外暴露） |
| 6379 | 内部 | TCP | Redis（不对外暴露） |
| 9090 | 内部 | HTTP | Prometheus（不对外暴露） |
| 3001 | 内部 | HTTP | Grafana（不对外暴露） |

---

## 三、部署前准备

### 1. 安装 Docker 和 Docker Compose

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# 重新登录使权限生效

# 验证
docker --version      # >= 24.0
docker compose version # >= 2.20
```

```bash
# CentOS / RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### 2. 获取项目代码

```bash
# 方式A: Git 克隆（推荐）
git clone <仓库地址> /opt/digital-doctor
cd /opt/digital-doctor

# 方式B: 压缩包解压
tar -xzf digital-doctor.tar.gz -C /opt/
cd /opt/digital-doctor
```

### 3. 配置环境变量

```bash
# 复制生产环境模板
cp .env.production .env

# 编辑 .env 文件（必须修改的项已标注）
vim .env
```

**必须修改的配置项：**

```ini
# ── 安全密钥（必须修改！）──
SECRET_KEY=<生成随机64位字符串>
PHI_ENCRYPTION_KEY=<生成Fernet密钥>

# ── 数据库 ──
DB_PASSWORD=<强密码>
POSTGRES_PASSWORD=<同DB_PASSWORD>

# ── 域名 ──
DOMAIN=doctor.your-hospital.com

# ── LLM API ──
LLM_API_KEY=<您的API Key>
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o

# ── 微信小程序（可选）──
WECHAT_APPID=<小程序AppID>
WECHAT_SECRET=<小程序AppSecret>

# ── 备份存储（可选）──
BACKUP_S3_BUCKET=<S3桶名>
BACKUP_S3_ENDPOINT=<S3端点>
```

**生成密钥命令：**

```bash
# SECRET_KEY
openssl rand -hex 32

# PHI_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. 准备 SSL 证书

```bash
# 创建证书目录
mkdir -p nginx/ssl

# 方式A: Let's Encrypt（推荐）
sudo apt install -y certbot
sudo certbot certonly --standalone -d doctor.your-hospital.com
sudo cp /etc/letsencrypt/live/doctor.your-hospital.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/doctor.your-hospital.com/privkey.pem nginx/ssl/

# 方式B: 自签名证书（仅测试）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

### 5. 创建备份目录

```bash
mkdir -p /opt/backups/digital-doctor
chmod 700 /opt/backups/digital-doctor
```

---

## 四、安装步骤

### 第1步：构建镜像

```bash
cd /opt/digital-doctor

# 构建后端
docker compose -f docker-compose.prod.yml build backend

# 构建前端
docker compose -f docker-compose.prod.yml build frontend

# 拉取基础镜像
docker compose -f docker-compose.prod.yml pull db redis
```

### 第2步：启动数据库

```bash
# 仅启动数据库和Redis
docker compose -f docker-compose.prod.yml up -d db redis

# 等待就绪（约10秒）
sleep 10
docker compose -f docker-compose.prod.yml ps
```

预期输出：db 和 redis 状态为 `Up (healthy)`

### 第3步：初始化数据库

```bash
# 运行数据库迁移
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 创建初始管理员账号
docker compose -f docker-compose.prod.yml run --rm backend python -m src.db.seed
```

初始管理员账号（部署后请立即修改）：
- 账号：`admin`
- 密码：输出在控制台，请记录

### 第4步：启动全部服务

```bash
docker compose -f docker-compose.prod.yml up -d

# 查看所有服务状态
docker compose -f docker-compose.prod.yml ps
```

预期所有服务状态为 `Up` 或 `Up (healthy)`。

### 第5步：验证部署

```bash
# 健康检查
curl https://doctor.your-hospital.com/health
# 预期: {"status":"healthy","checks":{...}}

# 就绪检查
curl https://doctor.your-hospital.com/health/ready
# 预期: {"status":"ready","database":"connected","redis":"connected"}

# API 端点
curl https://doctor.your-hospital.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone_hash":"admin","password":"<初始密码>"}'
# 预期: 返回 access_token + refresh_token

# 前端可访问
curl -I https://doctor.your-hospital.com/
# 预期: HTTP/2 200
```

### 第6步：（可选）启动监控栈

```bash
docker compose -f docker-compose.monitoring.yml up -d

# Grafana 访问
# URL: http://<服务器IP>:3001
# 默认账号: admin / admin（首次登录后修改）
```

---

## 五、HTTPS 配置

编辑 `nginx/nginx.conf`，确认以下配置已启用：

```nginx
server {
    listen 443 ssl http2;
    server_name doctor.your-hospital.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... 其余配置见 nginx/nginx.conf
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name doctor.your-hospital.com;
    return 301 https://$host$request_uri;
}
```

Let's Encrypt 证书自动续期：

```bash
# 添加 crontab 任务（每月1日凌晨3点续期）
sudo crontab -e
# 添加：
0 3 1 * * certbot renew --quiet --post-hook "docker compose -f /opt/digital-doctor/docker-compose.prod.yml restart nginx"
```

---

## 六、数据备份与恢复

### 设置自动备份

```bash
# 添加 crontab（每日凌晨2点全量备份）
sudo crontab -e
# 添加：
0 2 * * * /opt/digital-doctor/scripts/backup-db.sh full >> /var/log/ddd-backup.log 2>&1
```

### 手动备份

```bash
# 全量备份
/opt/digital-doctor/scripts/backup-db.sh full

# 备份文件位置
ls -la /opt/backups/digital-doctor/
# 文件名格式: backup_YYYYMMDD_HHMMSS.dump
```

### 恢复数据

```bash
# 查看可用备份
ls -la /opt/backups/digital-doctor/

# 恢复指定备份
/opt/digital-doctor/scripts/restore-db.sh /opt/backups/digital-doctor/backup_20260530_020000.dump

# 仅验证备份（不实际恢复）
/opt/digital-doctor/scripts/restore-db.sh --dry-run /opt/backups/digital-doctor/backup_20260530_020000.dump
```

---

## 七、日常运维

### 启动/停止/重启

```bash
# 启动
docker compose -f /opt/digital-doctor/docker-compose.prod.yml up -d

# 停止
docker compose -f /opt/digital-doctor/docker-compose.prod.yml stop

# 重启
docker compose -f /opt/digital-doctor/docker-compose.prod.yml restart

# 查看日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs -f --tail=100

# 查看特定服务日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs -f backend
```

### 更新版本

```bash
cd /opt/digital-doctor
git pull  # 或解压新版本压缩包

# 重新构建
docker compose -f docker-compose.prod.yml build

# 滚动更新（零停机）
docker compose -f docker-compose.prod.yml up -d --no-deps backend celery-worker

# 运行数据库迁移
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 健康检查
curl https://doctor.your-hospital.com/health
```

### 磁盘空间监控

```bash
# 检查磁盘使用
df -h /opt/

# 清理旧备份（保留30天）
find /opt/backups/digital-doctor/ -name "*.dump" -mtime +30 -delete

# 清理 Docker 无用镜像
docker system prune -a --filter "until=168h"
```

### 日志查看

```bash
# 应用日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs backend | grep ERROR

# Nginx 访问日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs nginx

# 数据库慢查询
docker compose -f /opt/digital-doctor/docker-compose.prod.yml exec db psql -U ddd -d digital_doctor -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

---

## 八、故障排查

### 服务无法启动

```bash
# 查看详细错误
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs <服务名>

# 常见原因：
# 1. 端口被占用 → netstat -tlnp | grep <端口>
# 2. 磁盘空间不足 → df -h
# 3. .env 配置错误 → 检查必须修改的配置项
```

### 数据库连接失败

```bash
# 测试数据库连通性
docker compose -f /opt/digital-doctor/docker-compose.prod.yml exec db pg_isready -U ddd

# 检查数据库日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs db | tail -50
```

### SSL 证书过期

```bash
# 检查证书有效期
openssl x509 -in /opt/digital-doctor/nginx/ssl/fullchain.pem -noout -dates

# 手动续期
sudo certbot renew
docker compose -f /opt/digital-doctor/docker-compose.prod.yml restart nginx
```

### API 返回 502

```bash
# 检查后端是否运行
docker compose -f /opt/digital-doctor/docker-compose.prod.yml ps backend

# 重启后端
docker compose -f /opt/digital-doctor/docker-compose.prod.yml restart backend

# 检查后端日志
docker compose -f /opt/digital-doctor/docker-compose.prod.yml logs backend | tail -50
```

---

## 九、安全加固清单

部署完成后，逐项确认：

- [ ] `.env` 中所有密码已修改为强密码
- [ ] SSL 证书已配置并启用 HTTPS
- [ ] PostgreSQL 端口(5432)未对外暴露
- [ ] Redis 端口(6379)未对外暴露
- [ ] 初始管理员密码已修改
- [ ] 自动备份 cron 已配置
- [ ] 备份文件已加密（`BACKUP_ENCRYPTION_ENABLED=true`）
- [ ] 服务器防火墙已配置（仅开放 443 端口）
- [ ] 操作系统已安装安全更新
- [ ] SSH 已禁用密码登录（仅密钥认证）

---

## 十、联系与支持

| 事项 | 联系方式 |
|------|---------|
| 技术支持 | {技术支持邮箱/电话} |
| 紧急故障 | {7x24紧急联系方式} |
| 文档目录 | `/opt/digital-doctor/docs/` |
| 日志目录 | `/var/log/ddd-*.log` |
| 备份目录 | `/opt/backups/digital-doctor/` |

---

*本手册随系统版本更新，最新版本请查看项目 `docs/manuals/deployment-guide.md`。*
