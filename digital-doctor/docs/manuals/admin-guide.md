# 管理员配置手册 — 数字医生分身系统

> **版本**: v1.0
> **适用对象**: 系统管理员、信息科运维人员
> **更新日期**: {YYYY年MM月DD日}
> **医院名称**: {医院名称}

---

## 目录

1. [系统部署架构概览](#一系统部署架构概览)
2. [科室与医生管理](#二科室与医生管理)
3. [指南参数配置说明](#三指南参数配置说明)
4. [备份与恢复操作](#四备份与恢复操作)
5. [监控看板解读](#五监控看板解读)
6. [告警处理流程](#六告警处理流程)
7. [应急预案](#七应急预案)

---

## 一、系统部署架构概览

### 1.1 整体架构

数字医生分身系统采用微服务容器化部署架构，基于Docker Compose编排：

```
                          互联网 (HTTPS)
                               │
                    ┌──────────▼──────────┐
                    │    Nginx 反向代理     │
                    │  (TLS终止 / WAF)     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  Frontend      │ │  Backend    │ │  MinIO      │
    │  (React/Node)  │ │  (FastAPI)  │ │  (S3备份)   │
    │  Port: 3000    │ │  Port: 8000 │ │  Port: 9000 │
    └────────────────┘ └──────┬──────┘ └─────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌──────▼──────────┐
    │  PostgreSQL 15 │ │  Redis 7   │ │  Celery Worker  │
    │  Port: 5432    │ │ Port: 6379 │ │  + Celery Beat  │
    └────────────────┘ └────────────┘ └─────────────────┘
              │               │
    ┌─────────▼──────────────▼──────────────┐
    │  Prometheus + Grafana (监控栈)         │
    │  Port: 9090 / 3000                    │
    └───────────────────────────────────────┘
```

### 1.2 服务端口清单

| 服务 | 内部端口 | 外部暴露 | 用途 |
|------|---------|---------|------|
| Nginx | 80, 443 | 443 | HTTPS反向代理 |
| Frontend | 3000 | 仅内网 | React前端应用 |
| Backend | 8000 | 仅内网 | FastAPI REST API |
| PostgreSQL | 5432 | 仅内网 | 主数据库 |
| Redis | 6379 | 仅内网 | 缓存/消息队列 |
| Prometheus | 9090 | 仅管理VPN | 指标采集 |
| Grafana | 3000 | 仅管理VPN | 监控面板 |
| MinIO | 9000, 9001 | 仅管理VPN | S3兼容对象存储 |

### 1.3 目录结构（服务器端）

```
/opt/digital-doctor/
├── docker-compose.yml              # 开发环境编排
├── docker-compose.prod.yml         # 生产环境编排
├── docker-compose.monitoring.yml   # 监控栈编排
├── backend/
│   ├── Dockerfile
│   ├── src/
│   └── backups/                    # 本地备份存储
├── frontend/
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts.yml
│   └── grafana/
│       └── provisioning/
├── scripts/
│   ├── backup-cron.sh
│   ├── restore-db.sh
│   ├── setup-db.sh
│   └── migrate-db.sh
└── .env                            # 环境变量（敏感信息）
```

### 1.4 启动与停止

```bash
# 启动全部服务（生产环境）
cd /opt/digital-doctor
docker compose -f docker-compose.prod.yml up -d

# 启动监控栈（可选）
docker compose -f docker-compose.monitoring.yml up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f backend

# 优雅停止
docker compose -f docker-compose.prod.yml down

# 停止并删除数据卷（危险操作！）
docker compose -f docker-compose.prod.yml down -v
```

### 1.5 健康检查

系统提供三个层级的健康检查端点：

| 端点 | 用途 | 正常响应 |
|------|------|---------|
| `/health/live` | Kubernetes Liveness Probe | `{"status": "ok"}` |
| `/health/ready` | Kubernetes Readiness Probe | `{"status": "ok", "database": "healthy", "redis": "healthy"}` |
| `/health` | 完整健康检查（含磁盘空间） | `{"status": "healthy", "checks": {...}}` |

Prometheus每15秒抓取`/metrics`端点获取系统指标。

---

## 二、科室与医生管理

### 2.1 创建科室

**操作路径**：登录管理员账号 -> "系统管理" -> "科室管理"

**步骤**：
1. 点击"新增科室"按钮
2. 填写以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 科室名称 | 科室全称 | `内分泌科` |
| 科室代码 | 唯一英文标识 | `endocrinology` |
| 所属院区 | 选择关联的医院ID（多院区场景） | {院区ID} |

3. 点击"确认创建"

[图片：科室管理页面截图]

### 2.2 管理医生

**操作路径**："系统管理" -> "医生管理"

**医生列表**显示所有已注册医生，包含：
- 姓名/职称
- 所属科室
- 执业证号
- 是否科室主任
- 管理患者数
- 账号状态（启用/停用）

**分配医生到科室**：
1. 在医生列表中找到目标医生
2. 点击"分配科室"
3. 在下拉列表中选择目标科室
4. 确认

**设置/取消科室主任**：
1. 在医生列表中找到目标医生
2. 点击"编辑"
3. 切换"是否科室主任"开关
4. 保存

### 2.3 账号管理

| 操作 | 说明 |
|------|------|
| 创建医生账号 | 通过后台数据库操作或管理API创建 |
| 停用账号 | 在"医生管理"中将is_active设为false |
| 重置密码 | 联系运维通过数据库操作 |

---

## 三、指南参数配置说明

### 3.1 可配置的临床参数

系统内置的临床指南参数可通过修改配置进行个性化调整。以下是关键可配置参数：

| 参数 | 默认值 | 说明 | 修改建议 |
|------|--------|------|---------|
| 空腹血糖目标 | 4.4-7.0 mmol/L | 糖尿病管理空腹血糖达标范围 | 根据医院内分泌科共识调整 |
| 餐后血糖目标 | <10.0 mmol/L | 餐后2小时血糖控制目标 | 根据最新CDS指南调整 |
| HbA1c目标 | <7.0% | 糖化血红蛋白控制目标（一般人群） | 可对不同年龄段设置不同值 |
| 低血糖阈值 | 3.9 mmol/L | 低于此值触发低血糖预警 | 标准值，一般不需修改 |
| 严重低血糖阈值 | 3.0 mmol/L | 低于此值触发危急预警 | 标准值，一般不需修改 |
| 高血糖警告阈值 | 10.0 mmol/L | 高于此值触发高血糖预警 | 可根据科室标准调整 |
| TIR目标范围 | 3.9-10.0 mmol/L | 目标范围内时间计算的血糖区间 | 标准值，一般不需修改 |
| TIR达标率 | >70% | 目标范围内时间占比的达标线 | 基于指南推荐 |

### 3.2 修改参数的方法

当前版本通过配置文件管理参数。修改步骤：

1. 登录服务器
2. 编辑 `backend/src/engine/rules/__init__.py` 中的规则定义
3. 重启backend服务：

```bash
docker compose -f docker-compose.prod.yml restart backend
```

### 3.3 通知模板配置

用药提醒和健康提示的内容模板可通过数据库`notification_templates`表管理。

---

## 四、备份与恢复操作

### 4.1 备份策略

| 备份类型 | 方式 | 频率 | 保留期限 |
|---------|------|------|---------|
| 全量备份 | pg_dump + gzip压缩 | 每日02:00 UTC | 30天 |
| 增量备份 | PostgreSQL WAL归档 | 每小时 | 7天 |
| 异地备份 | S3/MinIO同步 | 每日 | 30天 |

### 4.2 手动备份

通过API触发即时备份：

```bash
# 需管理员Token
curl -X POST https://{医院域名}/api/v1/admin/backups \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"backup_type": "full"}'
```

通过脚本备份：

```bash
cd /opt/digital-doctor
./scripts/backup-cron.sh full
```

### 4.3 备份列表查看

**在管理界面查看**："系统管理" -> "备份管理" 可看到备份记录列表，包含：
- 备份时间
- 备份类型（全量/增量）
- 文件大小
- 状态（进行中/完成/失败/已验证）
- SHA-256校验和

**通过API查看**：

```bash
curl https://{医院域名}/api/v1/admin/backups \
  -H "Authorization: Bearer {admin_token}"
```

### 4.4 备份校验

系统支持自动校验备份完整性：

```bash
# 校验指定备份
./scripts/backup-cron.sh verify <backup_id>

# 校验最新备份
./scripts/backup-cron.sh verify
```

校验项目包括：
- 文件是否存在
- 文件大小是否匹配记录
- SHA-256校验和是否一致

### 4.5 数据恢复

**从本地备份恢复**：

```bash
# 1. 列出可用备份
ls -la backups/backup_full_*.sql.gz

# 2. 试运行（验证备份可用性）
./scripts/restore-db.sh backup_full_20260115_020000.sql.gz --dry-run

# 3. 执行恢复
./scripts/restore-db.sh backup_full_20260115_020000.sql.gz

# 4. 运行迁移（确保schema最新）
cd backend && alembic upgrade head

# 5. 验证服务
curl http://localhost:8000/health
```

**从S3/MinIO恢复**：

```bash
# 1. 从S3下载备份
aws s3 cp s3://{bucket}/backup_full_20260115_020000.sql.gz ./backups/ \
  --endpoint-url ${BACKUP_S3_ENDPOINT}

# 2. 执行本地恢复（同上步骤2-5）
```

### 4.6 备份统计API

```bash
curl https://{医院域名}/api/v1/admin/backups/stats \
  -H "Authorization: Bearer {admin_token}"
```

返回数据包括：总备份数、成功备份数、失败备份数、成功率、总存储量、最近成功备份时间。

---

## 五、监控看板解读

### 5.1 监控系统架构

```
Backend (FastAPI)
    │
    ├── /metrics endpoint (Prometheus格式)
    │
    ▼
Prometheus (每15秒采集)
    │
    ├── 指标存储(TSDB)
    ├── 告警规则评估(alerts.yml)
    │
    ▼
Grafana (可视化仪表盘)
    │
    └── 数据源: Prometheus
```

### 5.2 关键监控指标

#### API层面指标

| 指标名 | 类型 | 说明 | 关注点 |
|--------|------|------|--------|
| `http_requests_total` | Counter | HTTP请求总数（按方法、端点、状态码） | 错误率突增可能是系统故障 |
| `http_request_duration_seconds` | Histogram | HTTP请求延迟分布（P95/P99） | P95 > 5s需关注 |

#### LLM使用指标

| 指标名 | 类型 | 说明 | 关注点 |
|--------|------|------|--------|
| `llm_requests_total` | Counter | LLM请求总数（按模型、状态） | fallback率 > 10%需检查LLM服务 |
| `llm_tokens_total` | Counter | LLM token消耗（输入/输出） | 成本监控，异常突增需排查 |

#### 临床运营指标

| 指标名 | 类型 | 说明 | 关注点 |
|--------|------|------|--------|
| `active_patients` | Gauge | 活跃患者数 | 监测系统使用量 |
| `alerts_unacknowledged` | Gauge | 未确认预警数 | >10个需催促医生处理 |
| `disk_free_pct` | Gauge | 磁盘可用空间百分比 | <20%需扩容，<10%为紧急 |

### 5.3 访问Grafana

1. 通过管理VPN访问 `http://{服务器IP}:3000`
2. 默认账号：admin / admin（首次登录需修改密码）
3. 系统预置了以下仪表盘：
   - **API Overview**：请求量、延迟、错误率趋势
   - **LLM Usage**：Token消耗、成功率、回退率
   - **Clinical Overview**：活跃患者、预警统计
   - **Infrastructure**：数据库连接、Redis、磁盘使用

[图片：Grafana仪表盘截图]

### 5.4 健康检查监控

建议在Prometheus中配置对`/health`端点的监控，当系统健康状态变为`unhealthy`时触发告警。

---

## 六、告警处理流程

### 6.1 Prometheus告警规则

系统预置了以下告警规则（位于`monitoring/prometheus/alerts.yml`）：

| 告警名称 | 触发条件 | 严重级别 | 处理建议 |
|---------|---------|---------|---------|
| **HighErrorRate** | 5xx错误率 > 5% (5分钟) | Warning | 检查backend日志，排查异常 |
| **HighLatency** | P95延迟 > 5秒 (5分钟) | Warning | 检查数据库/LLM服务响应 |
| **LLMFallbackRateHigh** | LLM回退率 > 10% (10分钟) | Warning | 检查LLM API密钥和网络 |
| **LLMErrorRateCritical** | LLM错误率 > 20% (5分钟) | Critical | 立即检查LLM服务可用性 |
| **DiskSpaceLow** | 磁盘可用 < 20% (5分钟) | Warning | 清理日志/过期备份，扩容 |
| **UnacknowledgedAlertsHigh** | 未确认预警 > 10 (5分钟) | Warning | 通知科室主任处理预警 |

### 6.2 标准告警处理流程

```
告警触发
    │
    ├── 1. 收到告警通知（邮件/消息）
    │
    ├── 2. 登录Grafana查看相关仪表盘
    │
    ├── 3. 判断严重级别
    │   ├── Warning → 正常工作时间处理
    │   └── Critical → 立即响应（含非工作时间）
    │
    ├── 4. 登录服务器查看应用日志
    │   docker compose logs -f backend --tail=100
    │
    ├── 5. 根据告警类型执行对应操作
    │   ├── 磁盘不足 → 清理 + 扩容
    │   ├── 服务异常 → 重启服务
    │   ├── LLM故障 → 切换API密钥/服务商
    │   └── 数据库异常 → 检查连接 + 恢复
    │
    ├── 6. 确认问题解决（Grafana指标恢复正常）
    │
    └── 7. 记录事件（时间、原因、处理措施、结果）
```

### 6.3 常见问题快速排障

| 现象 | 可能原因 | 检查命令 | 解决方案 |
|------|---------|---------|---------|
| 5xx错误率突增 | Backend崩溃或过载 | `docker compose logs backend --tail=50` | 查看日志定位异常，必要时重启 |
| 响应变慢 | 数据库连接池耗尽 | 查看DB连接数 | 增大`DB_POOL_SIZE`，优化慢查询 |
| LLM调用全部失败 | API密钥失效/额度用尽 | 检查`LLM_API_KEY` | 更新密钥或切换服务商 |
| 磁盘告警 | 备份文件累计过多 | `du -sh backups/` | 运行`cleanup`清理过期备份 |
| Redis连接失败 | Redis服务宕机 | `docker compose logs redis` | 重启Redis服务 |

---

## 七、应急预案

### 7.1 系统故障应急流程

#### 场景A：数据库服务故障

```
检测到数据库不可用
    │
    ├── [立即] 通知科室：系统暂不可用，请启用线下流程
    │
    ├── [0-15分钟] 检查PostgreSQL容器状态
    │   docker compose ps db
    │   docker compose logs db --tail=50
    │
    ├── [15-30分钟] 尝试恢复
    │   ├── 尝试重启: docker compose restart db
    │   ├── 检查磁盘空间: df -h
    │   └── 检查WAL日志是否写满磁盘
    │
    ├── [30-60分钟] 如无法恢复，启动数据库恢复流程
    │   ├── 定位最新备份
    │   ├── 准备新数据库实例
    │   └── 执行恢复: restore-db.sh
    │
    └── [恢复后] 验证 + 通知科室恢复使用
```

#### 场景B：应用服务故障

```
检测到Backend服务不可用
    │
    ├── [立即] 检查Backend容器状态
    │   docker compose ps backend
    │
    ├── [5分钟] 尝试重启
    │   docker compose restart backend
    │
    ├── [10分钟] 如重启失败，检查原因
    │   ├── 查看日志: docker compose logs backend --tail=100
    │   ├── 检查环境变量: docker compose exec backend env
    │   ├── 检查数据库连接
    │   └── 检查Redis连接
    │
    ├── [30分钟] 如无法修复，考虑回滚到上一个稳定版本
    │   git checkout <last-stable-tag>
    │   docker compose -f docker-compose.prod.yml up -d --build
    │
    └── [恢复后] 验证 + 记录事件
```

#### 场景C：LLM服务不可用

```
检测到LLM服务不可用
    │
    ├── [立即] 系统自动启用fallback模式（使用规则引擎替代）
    │   ├── AI健康教练：降级为基于关键词的规则回复
    │   ├── AI报告解读：降级为OCR识别+静态参考范围对比
    │   └── 风险评估：不受影响（基于本地规则引擎）
    │
    ├── [在系统恢复前] 通知科室：AI功能暂时降级，核心功能不受影响
    │
    ├── [运维] 排查LLM服务问题
    │   ├── 验证API密钥有效性
    │   ├── 检查LLM服务商状态页
    │   ├── 考虑切换备用LLM服务商
    │   └── 检查防火墙/代理配置
    │
    └── [恢复后] 验证LLM功能正常，通知科室
```

### 7.2 数据恢复步骤（详细）

详见 [灾备恢复计划](../disaster-recovery.md) 获取完整的数据库恢复操作流程。

**快速恢复清单**：

- [ ] 1. 评估故障范围：确定数据丢失时间点
- [ ] 2. 通知相关方：科室负责人、信息科领导
- [ ] 3. 定位备份文件：确定最近成功备份
- [ ] 4. 验证备份完整性：运行 `restore-db.sh --dry-run`
- [ ] 5. 准备目标环境：确保可用数据库实例
- [ ] 6. 执行数据恢复：运行 `restore-db.sh`
- [ ] 7. 运行数据库迁移：`alembic upgrade head`
- [ ] 8. 验证服务可用：`curl /health`
- [ ] 9. 通知恢复完成
- [ ] 10. 编写事件报告

### 7.3 应急联系人

| 角色 | 姓名 | 手机 | 邮箱 | 备注 |
|------|------|------|------|------|
| 系统管理员 | {填写} | {填写} | {填写} | 第一响应人 |
| 备份管理员 | {填写} | {填写} | {填写} | 负责数据恢复 |
| 科室信息联络人 | {填写} | {填写} | {填写} | 负责通知医生 |
| 医院信息科负责人 | {填写} | {填写} | {填写} | 重大事件决策 |
| 院外技术支持 | {填写} | {填写} | {填写} | 系统供应商 |

### 7.4 事件报告模板

```
事件编号: INC-{YYYY}-{NNN}
发生时间: {YYYY-MM-DD HH:mm}
发现时间: {YYYY-MM-DD HH:mm}
恢复时间: {YYYY-MM-DD HH:mm} (如已恢复)
影响范围: {描述受影响的功能和用户数}
根本原因: {描述导致故障的根本原因}
处理过程: {描述排查步骤和处理操作}
解决方案: {描述最终解决方案}
预防措施: {描述避免再次发生的措施}
报告人: {填写}
```

---

## 附录

### A. 环境变量完整清单

详见 `backend/.env.example` 或系统配置文件。

### B. 相关文档

- [灾备恢复计划](../disaster-recovery.md)
- [安全审计报告模板](../compliance/security-audit-report-template.md)
- [数据分类分级文档](../compliance/data-classification-policy.md)

### C. 系统运维速查

```bash
# 查看所有服务状态
docker compose -f docker-compose.prod.yml ps

# 重启单个服务
docker compose -f docker-compose.prod.yml restart <service_name>

# 查看服务日志
docker compose -f docker-compose.prod.yml logs -f --tail=50 <service_name>

# 数据库手动备份
./scripts/backup-cron.sh full

# 数据库恢复
./scripts/restore-db.sh <backup_file>

# 清理过期备份
./scripts/backup-cron.sh cleanup

# 查看磁盘使用
df -h && du -sh backups/
```

---

> **重要**: 系统管理员应至少每月检查一次备份完整性，每季度进行一次恢复演练。所有运维操作建议在变更窗口内进行，并提前通知相关科室。
