# 标书制作 AI 小程序 — 上线部署完整指南

---

## 第一步：微信小程序注册与配置

### 1.1 注册小程序账号（30 分钟）

1. 打开 [微信公众平台](https://mp.weixin.qq.com/)
2. 点击右上角"立即注册"，选择"小程序"
3. 填写邮箱（未注册过微信公众号的邮箱）、密码
4. 登录邮箱，点击激活链接
5. **主体类型选择"企业"**（个人主体无法开通微信支付）
6. 上传营业执照、填写企业信息、法人信息
7. 填写管理员信息（需要管理员微信扫码验证）
8. **微信认证**：支付 300 元/年的认证费（必须认证才能开通支付）
9. 等待审核通过（1-3 个工作日）

### 1.2 获取 AppID 和 AppSecret

1. 登录 [微信公众平台](https://mp.weixin.qq.com/) → 开发 → 开发管理 → 开发设置
2. 复制 **AppID（小程序ID）**，形如 `wx1234567890abcdef`
3. 点击 **AppSecret（小程序密钥）** → 重置 → 管理员扫码 → 复制密钥
4. 将这两个值填入 `.env` 文件：

```bash
WECHAT_APPID=wx1234567890abcdef
WECHAT_SECRET=your_app_secret_here
```

### 1.3 配置服务器域名白名单

1. 开发 → 开发管理 → 开发设置 → 服务器域名
2. 点击"修改"，填入以下域名（替换为你的真实域名）：

| 类型 | 域名 |
|------|------|
| request 合法域名 | `https://api.your-domain.com` |
| socket 合法域名 | `wss://api.your-domain.com`（如有） |
| uploadFile 合法域名 | `https://api.your-domain.com` |
| downloadFile 合法域名 | `https://api.your-domain.com` |

3. 保存后生效。注意：**必须 HTTPS，不能是 IP 地址，不能是 localhost**

### 1.4 安装微信开发者工具

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)（Windows/Mac 版）
2. 安装并登录（用管理员微信扫码）
3. 点击"+" → 导入项目
4. 目录选择：`E:\claude\bid-generator\miniprogram`
5. AppID 填入你在 1.2 获取的 AppID
6. 项目名称：`智能标书助手`
7. 点击"确定"进入开发界面

### 1.5 配置小程序代码

打开 `miniprogram/app.js`，修改第 5 行：

```javascript
// 修改前
apiBase: 'https://your-domain.com/api',

// 修改后（替换为你的真实域名）
apiBase: 'https://api.your-domain.com/api',
```

打开 `miniprogram/utils/api.js`，确保所有接口路径正确。

### 1.6 添加 tabBar 图标

在 `miniprogram/images/` 目录下放置 6 张图标（可先用纯色方块测试）：

| 文件名 | 用途 | 尺寸 |
|--------|------|------|
| `tab-home.png` | 首页（未选中） | 40x40 px |
| `tab-home-active.png` | 首页（选中） | 40x40 px |
| `tab-template.png` | 模板（未选中） | 40x40 px |
| `tab-template-active.png` | 模板（选中） | 40x40 px |
| `tab-mine.png` | 我的（未选中） | 40x40 px |
| `tab-mine-active.png` | 我的（选中） | 40x40 px |

> 临时方案：去 [iconfont.cn](https://www.iconfont.cn/) 搜索并下载对应图标

### 1.7 真机预览测试

1. 在微信开发者工具中，点击工具栏的"预览"
2. 用手机微信扫码
3. 在手机上体验完整流程

---

## 第二步：微信支付开通

### 2.1 申请微信支付商户号（1-3 个工作日）

1. 登录 [微信公众平台](https://mp.weixin.qq.com/) → 功能 → 微信支付
2. 点击"开通"，填写商户信息：
   - 经营信息：选择"软件/IT服务"类目
   - 商户简称：`标书助手`
   - 联系信息：填写真实手机号和邮箱
3. 提交营业执照、法人身份证、对公账户信息
4. **超级管理员**：指定一个人（可以是法人自己），扫码绑定
5. 等待审核通过（微信支付会打一笔小额验证款到对公账户）

### 2.2 获取支付密钥

审核通过后，登录 [微信支付商户平台](https://pay.weixin.qq.com/)：

1. **获取商户号（MCHID）**
   - 账户中心 → 商户信息 → 复制"商户号"

2. **设置 APIv3 密钥**
   - 账户中心 → API 安全 → APIv3 密钥 → 设置
   - 随机生成 32 位字符串（例如用 `openssl rand -hex 16`）
   - **务必保存好，只显示一次**

3. **下载商户证书**
   - 账户中心 → API 安全 → API 证书 → 申请证书
   - 下载后得到三个文件：
     - `apiclient_key.pem`（商户私钥）
     - `apiclient_cert.pem`（商户证书）
     - `apiclient_cert.p12`（备用格式）
   - 将文件保存到服务器安全目录

4. **配置支付回调地址**
   - 产品中心 → 开发配置 → JSAPI 支付 → 支付回调地址
   - 填入：`https://api.your-domain.com/api/payment/notify/wechat`

### 2.3 配置 .env 支付参数

```bash
WECHAT_MCHID=1234567890           # 商户号
WECHAT_API_V3_KEY=your_32_char_key  # APIv3 密钥
WECHAT_NOTIFY_URL=https://api.your-domain.com/api/payment/notify/wechat
WECHAT_CERT_PATH=/etc/ssl/wechat/apiclient_cert.pem
WECHAT_KEY_PATH=/etc/ssl/wechat/apiclient_key.pem
```

---

## 第三步：云服务器购买与部署

### 3.1 购买服务器（10 分钟）

以阿里云为例（腾讯云流程类似）：

1. 打开 [阿里云 ECS](https://ecs.console.aliyun.com/)
2. 点击"创建实例"
3. 配置选择：

| 配置项 | 推荐值 | 月费（参考） |
|--------|--------|------------|
| 地域 | 离用户最近的（如华东1-杭州） | - |
| 实例规格 | 2 vCPU + 4 GiB 内存 | ~150 元/月 |
| 系统盘 | 40 GB ESSD | ~30 元/月 |
| 操作系统 | Ubuntu 22.04 LTS 64位 | - |
| 带宽 | 按量计费，5 Mbps 峰值 | ~100 元/月 |

4. 设置 root 密码（牢记）
5. 创建并支付
6. 实例创建后，记录 **公网 IP**（如 `47.96.xxx.xxx`）

### 3.2 域名注册与备案（1-2 周）

1. 在阿里云/腾讯云注册域名，如 `bid-ai.cn`（~50 元/年）
2. 进入域名控制台 → 解析 → 添加记录：

| 类型 | 主机记录 | 记录值 |
|------|---------|--------|
| A | @ | 服务器公网 IP |
| A | api | 服务器公网 IP |
| A | www | 服务器公网 IP |

3. **ICP 备案**（中国大陆服务器必须）
   - 阿里云控制台 → 备案 → 开始备案
   - 上传营业执照、法人身份证
   - 填写网站信息（网站名称：标书助手）
   - 提交后等待管局审核（通常 7-15 个工作日）

### 3.3 服务器初始化（30 分钟）

SSH 连接到服务器：

```bash
ssh root@你的服务器IP
```

#### 3.3.1 基础环境

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y curl wget git vim build-essential nginx certbot python3-certbot-nginx

# 安装 Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 验证
node --version   # 应显示 v20.x
npm --version    # 应显示 10.x

# 安装 Python 3.11
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 安装 MySQL 8.0
apt install -y mysql-server
mysql_secure_installation  # 按提示设置 root 密码
```

#### 3.3.2 创建 MySQL 数据库

```bash
mysql -u root -p
```

在 MySQL 命令行中执行：

```sql
CREATE DATABASE bid_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'biduser'@'localhost' IDENTIFIED BY 'your_strong_password_here';
GRANT ALL PRIVILEGES ON bid_generator.* TO 'biduser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 3.3.3 安装 Redis

```bash
apt install -y redis-server
systemctl enable redis-server
systemctl start redis-server
```

#### 3.3.4 上传项目代码

```bash
# 在服务器上
mkdir -p /var/www/bid-generator
cd /var/www/bid-generator

# 在本地电脑执行（把代码传到服务器）
# 打开新终端窗口：
scp -r E:\claude\bid-generator\backend root@你的IP:/var/www/bid-generator/
scp -r E:\claude\bid-generator\gateway root@你的IP:/var/www/bid-generator/
scp -r E:\claude\bid-generator\admin root@你的IP:/var/www/bid-generator/
scp E:\claude\bid-generator\.env.example root@你的IP:/var/www/bid-generator/.env
```

### 3.4 配置 Python 后端

```bash
cd /var/www/bid-generator/backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install python-dotenv pymysql

# 编辑 .env 文件
vim /var/www/bid-generator/.env
```

`.env` 文件内容：

```bash
# 服务器配置
PORT=8000
GATEWAY_PORT=3000
ENVIRONMENT=production

# MySQL 数据库（替换密码）
DATABASE_URL=mysql+pymysql://biduser:your_password@127.0.0.1:3306/bid_generator

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# JWT 密钥（随机生成）
JWT_SECRET=$(openssl rand -hex 32)

# DeepSeek API
DEEPSEEK_API_KEY=sk-707a90a4206b45e9962d606d7a6434f3
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 微信小程序
WECHAT_APPID=wx_your_appid
WECHAT_SECRET=your_app_secret

# 微信支付
WECHAT_MCHID=your_mchid
WECHAT_API_V3_KEY=your_api_v3_key
WECHAT_NOTIFY_URL=https://api.your-domain.com/api/payment/notify/wechat
WECHAT_CERT_PATH=/etc/ssl/wechat/apiclient_cert.pem
WECHAT_KEY_PATH=/etc/ssl/wechat/apiclient_key.pem
```

### 3.5 配置 Node.js 网关

```bash
cd /var/www/bid-generator/gateway
npm install
```

### 3.6 使用 PM2 管理进程

```bash
npm install -g pm2

# 启动 Python 后端
cd /var/www/bid-generator/backend
source venv/bin/activate
pm2 start main.py --name "bid-backend" --interpreter python3.11 -- --host 0.0.0.0 --port 8000

# 启动 Node.js 网关
cd /var/www/bid-generator/gateway
pm2 start server.js --name "bid-gateway"

# 设置开机自启
pm2 save
pm2 startup

# 查看运行状态
pm2 status
```

### 3.7 配置 Nginx + HTTPS

#### 3.7.1 Nginx 配置

```bash
vim /etc/nginx/sites-available/bid-generator
```

写入以下内容：

```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    # 文件上传限制
    client_max_body_size 50m;

    # 代理到 Node.js 网关
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式响应支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

```bash
# 启用站点
ln -s /etc/nginx/sites-available/bid-generator /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

#### 3.7.2 申请 SSL 证书（HTTPS）

```bash
# 使用 Let's Encrypt 免费证书
certbot --nginx -d api.your-domain.com

# 按提示输入邮箱，同意协议
# 选择 redirect（HTTP 自动跳转 HTTPS）

# 证书自动续期（已自动配置）
certbot renew --dry-run
```

### 3.8 防火墙配置

```bash
# 阿里云安全组（在阿里云控制台操作）
# 入方向规则：
# - 22 (SSH)
# - 80 (HTTP)
# - 443 (HTTPS)

# 服务器本地防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 3.9 验证部署

```bash
# 在服务器上测试
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:3000/health

# 从外部测试（在本地电脑执行）
curl https://api.your-domain.com/api/health
```

应返回：
```json
{"status":"ok","version":"2.0.0","message":"服务运行正常"}
```

---

## 第四步：小程序提交审核与发布

### 4.1 提交代码审核

1. 在微信开发者工具中，确认所有功能在真机上测试通过
2. 点击"上传"按钮，填写版本号和备注，如 `v1.0.0 - 初始版本`
3. 登录 [微信公众平台](https://mp.weixin.qq.com/) → 管理 → 版本管理
4. 在"开发版本"中找到刚上传的版本，点击"提交审核"
5. 填写审核信息：
   - **服务类目**：工具 → 办公
   - **配置功能页面**：填写首页路径 `pages/index/index`
   - **测试账号**：如需要登录才能使用，提供测试账号
6. 提交审核，等待 1-7 个工作日

### 4.2 审核通过后发布

1. 审核通过后，在"审核版本"中点击"发布"
2. 发布后用户即可在微信中搜索和使用

---

## 费用汇总

| 项目 | 费用 | 周期 |
|------|------|------|
| 微信小程序认证 | 300 元 | 每年 |
| 云服务器 ECS（2核4G） | ~200 元/月 | 每月 |
| MySQL 云数据库（可选） | ~100 元/月 | 每月 |
| 域名注册 | ~50 元 | 每年 |
| SSL 证书（Let's Encrypt） | 免费 | - |
| DeepSeek API | 按量 ~0.05 元/次 | - |
| **首年总投入** | **约 6000-8000 元** | - |

---

## 常见问题

**Q: 备案期间能测试吗？**
A: 可以。备案期间使用服务器 IP 直连测试（仅限开发版，无法提交审核）。

**Q: 个人主体能做吗？**
A: 不能。微信支付要求企业主体，个人主体无法开通支付功能。

**Q: 没有对公账户怎么办？**
A: 注册公司时银行会开对公账户。如果是新公司还没开户，可以先去银行开基本户。

**Q: 可以用香港服务器吗？**
A: 可以。香港服务器无需 ICP 备案，但国内用户访问速度较慢。
