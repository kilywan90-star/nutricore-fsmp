# 超声报告语音结构化系统

医生口述超声所见，AI 自动生成规范化、带 ICD-10 编码的结构化超声报告。面向超声科医生，15 秒完成一份报告。

[![Version](https://img.shields.io/badge/version-4.2-blue)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.12+-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow)](https://opensource.org/licenses/MIT)

## 解决的问题

超声科医生日均完成 80-150 例检查，每例报告需手动敲 200-400 字。口述 + AI 自动生成可将报告时间从 3 分钟压到 15 秒，且自带 ICD-10 编码和医保合规校验。

## 核心能力

- **语音录入**：浏览器录音 → 阿里云百炼 ASR 实时转写，支持湘普/川普方言纠错
- **ABCDEF 流水线**：ASR→自由 LLM→正则引擎→增强处理→模板匹配→交叉验证，6 路并行择优
- **340 条正式模板**：长沙范本 CSV，覆盖腹部/妇产/心脏/甲状腺/乳腺/泌尿/血管 7 大类
- **ICD-10 自动编码**：500+ 疾病编码表，诊断输出即带标准编码
- **医保 DRG/DIP 合规**：模板术语规范化，避免"可能性大"等拒付表述
- **逐条审核卡片**：保留/删除机制，医生最终确认后一键发送 PACS

## 快速开始

### 环境要求

Python 3.12+，无 GPU 依赖，4GB 内存即可运行。

### 安装

```bash
git clone <repo-url> ultrasound-report-mvp
cd ultrasound-report-mvp
pip install -r backend/requirements.txt
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`，填入 API Key：

```env
DASHSCOPE_API_KEY=sk-xxxxxxxx    # 阿里云百炼（语音识别）
DEEPSEEK_API_KEY=sk-xxxxxxxx     # DeepSeek（报告结构化）
TEMPLATE_DIR=./templates         # 模板 CSV 目录
TEMPLATE_CSV=./templates/1长沙范本.csv
```

### 启动

```bash
# 工作站（含前端页面，端口 9999）
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 9999

# API 网关（对外开放，端口 8800）
cd .. && python -m uvicorn microservice.main:app --host 0.0.0.0 --port 8800
```

浏览器打开 `http://localhost:9999`

## 使用流程

| 步骤 | 操作 | 快捷键 |
|------|------|--------|
| 1. 选患者 | 左侧队列点击患者，或输入姓名/性别/年龄/检查类型入队 | — |
| 2. 录音 | 点击红色录音按钮，口述超声所见 | `Ctrl+R` |
| 3. 转写 | 录音停止后自动调用 ASR，文本出现在识别框 | — |
| 4. 结构化 | 点击"结构化提取"或录音停止自动触发 | — |
| 5. 审核 | 逐条查看超声提示卡片，删除不需要的，恢复误删的 | — |
| 6. 保存 | 保存草稿至本地 SQLite | `Ctrl+S` |
| 7. 发送 | 确认无误，发送至 PACS | `Ctrl+Enter` |

## 项目结构

```
ultrasound-report-mvp/
├── backend/                        # 核心后端
│   ├── main.py                    # FastAPI 主程序（/api/structure 等）
│   ├── db.py                      # SQLite 患者/报告/审计数据库
│   ├── llm_client.py              # DeepSeek 结构化提取（ABCDEF流水线核心）
│   ├── asr_client.py              # 阿里云百炼语音识别
│   ├── asr_correction.py          # ASR 方言纠错（湘普/川普 → 标准术语）
│   ├── template_loader.py         # 模板加载器（340条CSV → 内存索引）
│   ├── template_anchor.py         # 模板精确匹配（部位路由+关键词打分+否定检测）
│   ├── template_filler.py         # 正则模板填充引擎
│   ├── template_fill_anchored.py  # 模板锚定填充（变量占位符替换）
│   ├── template_fetal.py          # 胎儿超声专用模板
│   ├── fixed_template_engine.py   # 固定模板引擎（意图识别+字段抽取）
│   ├── rule_engine.py             # 规则引擎（master_rules.json 配置驱动）
│   ├── knowledge/                 # 知识库
│   │   ├── master_rules.json      # 主规则库（242KB, 2100+ 条目）
│   │   ├── template_tags_v2.json  # 模板标签索引（278KB, 980 个模板标签）
│   │   ├── template_fields.json   # 模板字段定义（1.1MB, 2119 字段）
│   │   ├── exam_part_routing.json # 检查部位路由规则
│   │   ├── dialect_mapping.json   # 方言 → 标准术语映射
│   │   ├── sex_guard_rules.json   # 性别冲突检测规则
│   │   └── ...                    # 混淆词纠正/正常值范围/ICD-10/LOINC 等
│   ├── api_platform/              # 对外开放 API 子系统
│   │   ├── admin.py               # 管理后台
│   │   ├── auth.py                # API Key 鉴权
│   │   ├── billing.py             # 计费（按调用量阶梯定价）
│   │   ├── ratelimit.py           # 速率限制
│   │   └── db.py                  # 租户/API Key 管理数据库
│   └── templates/                 # 模板文件
│       ├── 1长沙范本.csv          # 长沙医院超声模板（595条DISCNAME, 136KB）
│       └── 超声模板.csv           # 同上（template_loader 固定文件名）
├── microservice/                   # API 网关微服务（端口 8800）
│   ├── main.py                    # /v1/structure /v1/transcribe /v1/signup 等
│   ├── pipeline.py                # 核心流水线编排（ASR→校正→模板匹配→LLM→验证）
│   ├── circuit_breaker.py         # LLM 熔断器（超时自动降级到规则引擎）
│   ├── schema.py                  # Pydantic 数据模型
│   └── config.py                  # 服务配置
├── frontend/                       # 前端
│   ├── index.html                 # 工作站主页（单文件 SPA）
│   ├── developer.html             # API 开发者文档页
│   ├── admin.html                 # 管理后台页
│   ├── dashboard.html             # 运营看板页
│   └── ...
├── docs/                           # 架构文档
│   ├── architecture.html          # 系统架构图
│   └── rule_flow_v2.1.html        # 规则引擎流程图
├── extension/                      # Chrome 浏览器扩展（脚踏板 F4 控制）
│   ├── content.js                 # PACS 页面嵌入侧边栏
│   ├── popup.html/popup.js        # 弹窗控制
│   └── sidebar.css                # 侧边栏样式
├── .env.example
├── Dockerfile
├── docker-compose.yml              # 双服务：API(8800) + Web(9999)
└── regression_test.py             # 10 条回归测试套件
```

## API 端点

### 工作站（端口 9999）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 工作站前端页面 |
| GET | `/api/health` | 健康检查 |
| POST | `/api/structure` | 文本 → 结构化报告（核心） |
| POST | `/api/transcribe` | 音频 → 转写文本 + audio_id |
| POST | `/api/patients/quick-add` | 快捷添加患者 |
| GET | `/api/patients/queue` | 患者队列 |
| POST | `/api/reports/{id}/save` | 保存报告 |
| POST | `/api/reports/{id}/send` | 发送至 PACS |

### API 网关（端口 8800）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/signup` | 开发者自助注册 |
| POST | `/v1/transcribe` | 语音转录+结构化（计费） |
| POST | `/v1/structure` | 纯文本结构化（计费） |
| GET | `/v1/usage` | 查询租户用量 |
| GET | `/v1/health` | 健康检查 |

## 回归测试

```bash
cd backend
python regression_test.py           # 本地 localhost:8730
python regression_test.py --remote  # 云服务器 47.109.151.238:9999
```

10 条用例覆盖腹部/妇产/心脏/甲状腺/乳腺/边缘场景，自动输出：
- 字段填充率（目标 > 80%）  
- 幻觉数字检测（LLM 输出数值是否在 ASR 原文中存在）
- 模板覆盖率（命中正式模板的比例）
- ICD-10 覆盖率
- 每次运行生成 `regression_snapshot_*.json` 快照，可对比版本间差异

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI |
| 前端 | 原生 HTML/CSS/JS（单文件 SPA，无构建步骤） |
| ASR | 阿里云百炼 qwen3-asr-flash |
| LLM | DeepSeek V4-Flash / DeepSeek-Chat |
| 数据库 | SQLite（WAL 模式，线程安全） |
| 部署 | Docker Compose（api + web 双服务） |
| 浏览器扩展 | Chrome Extension Manifest V3（脚踏板 F4 控制） |

## 适用场景

- **超声科日常报告**：腹部/妇产/心脏/甲状腺/乳腺/泌尿/血管
- **体检中心批量出报告**：正常报告快速通道（< 100ms，跳过 LLM）
- **医联体远程阅片**：API 网关对外开放，第三方 HIS/PACS 对接
- **教学培训**：口述对照 AI 输出，快速掌握规范化报告写作

## 开发

```bash
# 启动本地工作站
cd backend && uvicorn main:app --host 0.0.0.0 --port 8730 --reload

# 启动 API 网关
cd .. && uvicorn microservice.main:app --host 0.0.0.0 --port 8800 --reload

# 运行回归测试
cd backend && python regression_test.py

# Docker 部署
docker compose up -d
```

## License

MIT
