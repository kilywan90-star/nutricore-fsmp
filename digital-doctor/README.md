# 数字医生分身 (Digital Doctor Avatar)

内分泌科M1最小可用版本 — 患者端H5 + 医生端Web + AI辅助决策

## 快速开始

```bash
cd digital-doctor
docker compose up -d
```

- 后端 API: http://localhost:8000
- 患者端 H5: http://localhost:3000/patient
- 医生端 Web: http://localhost:3000/doctor
- Health check: http://localhost:8000/health

## 技术栈

- Backend: Python 3.10+, FastAPI, SQLAlchemy 2.0, PostgreSQL 15, Redis 7
- Frontend: React 18, TypeScript, Vite, Ant Design, ECharts
- AI: LLM 服务（OpenAI 兼容 API）
