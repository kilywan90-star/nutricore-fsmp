# 数字医生分身 (Digital Doctor Avatar)

内分泌科AI辅助诊疗系统 -- M1最小可用版本。

## 架构

```
患者端H5 (React + Ant Design)  →  FastAPI 后端  →  PostgreSQL CDR + Redis 缓存
医生端Web (React + Ant Design)       ↑
                                 规则引擎 (本地JSON规则 + LLM推理)
```

## 核心功能

- **患者端**: 糖尿病风险评估、AI报告解读、用药提醒、血糖记录与分析、AI健康教练
- **医生端**: 患者管理、指标趋势、异常预警
- **FHIR R4适配器**: 检验检查数据标准化导入
- **指南规则引擎**: 基于《中国2型糖尿病防治指南(2024版)》的14条核心规则

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| 数据库 | PostgreSQL 15, Redis 7 |
| 前端 | React 18, TypeScript, Vite, Ant Design, ECharts |
| 部署 | Docker Compose, Dockerfile |

## 快速启动

```bash
# 启动全部服务
docker compose up -d

# 验证健康检查
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}

# 患者端 http://localhost:3000/patient
# 医生端 http://localhost:3000/doctor
```

## 目录结构

```
digital-doctor/
├── backend/                  # FastAPI后端
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   └── src/
│       ├── main.py           # FastAPI app入口
│       ├── config.py         # 环境配置
│       ├── db/               # 数据库会话
│       ├── models/           # 数据模型
│       ├── schemas/          # Pydantic请求/响应模型
│       ├── security/         # PHI脱敏、加密、审计
│       ├── engine/           # 规则引擎
│       ├── services/         # 业务服务
│       ├── adapters/         # FHIR适配器
│       └── api/              # REST API路由
├── frontend/                 # React前端
├── docker-compose.yml
└── README.md
```
