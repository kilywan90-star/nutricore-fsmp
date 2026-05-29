# 渔伴 Yuban — 钓鱼社交小程序

## 项目结构

```
yuban/
├── backend/           # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置管理
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── api/             # API 路由
│   │   ├── services/        # 业务逻辑层
│   │   └── utils/           # 工具函数
│   ├── scripts/
│   │   ├── scrape_amap.py   # 高德POI数据爬取
│   │   └── seed_data.py     # 种子数据导入
│   └── requirements.txt
├── mini-program/      # 微信小程序前端
│   └── miniprogram/
│       └── pages/           # 页面
└── data/              # 爬取数据
```

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 设置环境变量
export AMAP_API_KEY=your_amap_key
export QWEATHER_API_KEY=your_qweather_key  # 可选

# 爬取钓点数据
python scripts/scrape_amap.py

# 导入数据库
python scripts/seed_data.py

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API文档: http://localhost:8000/docs

### 2. 小程序

1. 下载[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开 `mini-program/` 目录
3. 配置 `project.config.json` 中的 appid
4. 编译预览

### 3. 关键API Key获取

| 服务 | 注册地址 | 用途 |
|-----|---------|------|
| 高德地图 | https://console.amap.com/dev/ | POI搜索 + 天气 |
| 和风天气 | https://dev.qweather.com/ | 逐小时天气（可选） |
| 微信小程序 | https://mp.weixin.qq.com/ | 小程序AppID |
