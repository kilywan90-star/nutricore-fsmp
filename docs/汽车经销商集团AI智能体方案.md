# 汽车经销商集团 AI 智能体建设方案

---

# 第一部分：需求分析与架构建议

## 一、智能体数量分析

从需求文档看，这**不是一个多智能体系统**。文档 1.2 节明确指出：

> 建设 1 个统一 AI 智能体：政策文档中枢智能体

但如果按"能力边界"来拆，实际隐含以下能力模块，每个都可以是一个独立的 Agentic 单元：

| # | 能力模块 | 职责 | 是否独立智能体 |
|---|---------|------|:---:|
| 1 | **文档解析引擎** | PDF/Word/图片/扫描件解析、去水印、去页眉页脚、多栏排版、压缩包解压、密码读取 | 是（工具型） |
| 2 | **文档解读 + 结构化提取** | 提取主题、品牌、车型、时间、返利规则、考核口径、风险条款等 | 是（核心） |
| 3 | **文档自动分类** | 按业务类型（发布/过程/通报）、业务域（销售/财务/保险等8个）、品牌（长城/奇瑞等）三维分类 | 可合并到#2 |
| 4 | **专项分析** | 同类型多文档对比、版本变更识别（新增/删除/调整）、分析结论+风险点+执行建议 | 是（分析型） |
| 5 | **待办提取** | 待办动作、责任部门/人、截止时间、反馈要求、需提交材料 | 可合并到#2 |
| 6 | **对话问答** | 自然语言查询、多轮对话、权限过滤、来源标注 | 是（交互型） |
| 7 | **钉钉触发层** | 推送、待办创建、日程同步、多级提醒、强提醒 | 否（复用钉钉原生能力） |

**结论：3-4 个独立智能体即可覆盖全部需求。**

---

## 二、推荐架构：3 个 Agent + 1 个编排层

```
┌─────────────────────────────────────────────┐
│              钉钉入口（工作台/聊天/助手）         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Agent 0: 对话路由 + 权限网关            │
│   自然语言理解 → 意图识别 → 分发到对应 Agent      │
│   权限校验（复用钉钉组织架构）                    │
└───┬──────────────┬──────────────┬───────────┘
    │              │              │
┌───▼───┐    ┌─────▼──────┐   ┌──▼──────────┐
│Agent 1│    │  Agent 2   │   │  Agent 3    │
│文档处理│    │  专项分析   │   │  对话问答    │
│       │    │            │   │             │
│解析PDF│    │ 多文档对比  │   │ RAG检索     │
│OCR识别│    │ 版本变更    │   │ 多轮对话    │
│结构提取│    │ 风险识别    │   │ 权限过滤    │
│分类标签│    │ 执行建议    │   │ 来源标注    │
│待办提取│    │            │   │             │
└───┬───┘    └─────┬──────┘   └──┬──────────┘
    │              │              │
┌───▼──────────────▼──────────────▼──────────┐
│            共享能力层（非 Agent）              │
│  向量库 │ 知识库 │ 文件存储 │ 钉钉API          │
│  全部本地私有化部署                           │
└─────────────────────────────────────────────┘
```

---

## 三、模型选择

| 层级 | 推荐方案 | 原因 |
|------|---------|------|
| **文档解析+OCR** | PaddleOCR + MinerU 本地部署 | 无 API 成本，数据不出内网 |
| **文档解读+分类+待办提取** | DeepSeek-V3 / 通义千问 Qwen3 | 长文本理解强，结构化输出稳定 |
| **多文档对比分析** | 同上，需要大 context window | 动辄几十页政策文件对比，需要大窗口 |
| **对话问答(RAG)** | Embedding 模型 BGE-M3 本地部署 + DeepSeek | 本地 embedding 零成本，检索质量高 |
| **意图路由** | 规则 + 轻量模型 | 意图分类不需要大模型 |

---

## 四、部署成本对比

| 方案 | 初期投入 | 运营成本 | 推荐度 |
|------|---------|---------|:---:|
| **纯 SaaS API**（如通义千问/DeepSeek API） | 低 | 中等（按 token 计费） | ★★★ |
| **混合部署**：Embedding + 文档解析本地，LLM 用 API | 中 | 低-中 | ★★★★★ |
| **全私有化部署**（本地 GPU 服务器跑全部模型） | 高（GPU 服务器 10-30 万） | 低 | ★★★ |

**推荐混合部署：**
- **本地部署**：文档解析（PaddleOCR / MinerU）、Embedding 模型（BGE-M3）、向量库（Milvus Lite / Qdrant）、文件存储
- **API 调用**：LLM 推理层（解读、分析、对话），选 DeepSeek 或通义千问的商业 API
- **钉钉集成**：完全复用钉钉原生待办/日历/推送，零开发成本

优势：数据不出内网（原始文件、向量库都在本地）、LLM 成本可控（DeepSeek 百万 token 几块钱）、部署复杂度低（一台服务器即可）。

---

## 五、关键风险点

1. **文档解析是最大难点** — 扫描件、水印、多栏排版、表格混排，这些不是 LLM 能解决的，必须靠专业的文档解析 pipeline。建议优先验证这个环节。

2. **品牌权限隔离** — 需要在知识库层面做严格的 metadata 标注 + 检索过滤，不是模型层面能解决的。

3. **RAG 的"仅回答知识库已有内容"约束** — 需要做好 prompt 工程 + 检索阈值控制，加一个"无匹配时直接拒绝"的硬约束。

4. **一期范围控制** — 先做 1-2 个品牌、2-3 个业务域跑通全流程，验证效果后再扩展。

---

## 六、总结

| 维度 | 结论 |
|------|------|
| **智能体数量** | 3-4 个（文档处理、专项分析、对话问答 + 路由网关） |
| **推荐架构** | 混合部署：文档解析+向量库本地，LLM 用国产 API |
| **成本最优路径** | 一期聚焦 1 品牌 2 业务域，验证文档解析 pipeline → RAG 问答 → 待办闭环 |
| **最大风险点** | 扫描件/复杂排版文档解析准确率，建议先做 PoC 验证 |

---

# 第二部分：PoC 验证方案

## 0. PoC 目标

用**最少投入**验证核心链路可行性，回答一个关键问题：

> 真实厂商政策文件 → 结构化数据 → 钉钉待办，这条链路能不能跑通？准确率够不够？

---

## 1. PoC 范围（2 周）

### 做

- 选取 **1 个品牌（长城）、2 个业务域（销售、售后）**
- 覆盖 **3 种文件类型**：PDF（电子版）、扫描件（图片型 PDF）、Word
- 验证 **4 个核心环节**：文档解析 → 结构化提取 → 自动分类 → 待办抽取
- 接入 **钉钉待办 API**，创建一条真实待办

### 不做

- 不接向量库 / RAG 对话（二期验证）
- 不做多文档对比分析（二期验证）
- 不做钉钉工作台集成（一期开发做）
- 不处理密码文件、压缩包（解析库天然支持，不需要专门验证）

---

## 2. 技术选型

### 2.1 文档解析层

| 文件类型 | 推荐工具 | 备选 | 说明 |
|---------|---------|------|------|
| 电子版 PDF | **Docling** (IBM) 或 **MinerU** (opendatalab) | PyMuPDF | 二者对表格、多栏排版效果好，MinerU 中文更优 |
| 扫描件/图片 PDF | **PaddleOCR** + MinerU | Tesseract | PaddleOCR 中文识别率 97%+，支持表格识别 |
| Word (.docx) | **python-docx** + Mammoth | libreoffice 转换 | 直接解析 XML 结构，保真度高 |
| 图片 (.jpg/.png) | **PaddleOCR** | - | 同上 |
| 表格提取 | **MinerU** 内置表格模型 | Camelot / Tabula | 有表格线和无表格线的都能处理 |

**推荐组合**：MinerU 作为主力解析引擎（PDF/扫描件/表格通吃），PaddleOCR 作为 OCR 后备，python-docx 处理 Word。

### 2.2 LLM 层

| 用途 | 推荐模型 | 说明 |
|------|---------|------|
| 结构化信息提取 | **DeepSeek-V3** 或 **通义千问 Qwen3-235B** | 长文本理解能力强，支持 JSON 结构化输出 |
| 文档分类 | 同上，或轻量模型如 Qwen3-8B | 分类任务可本地部署小模型，零 API 成本 |
| 待办提取 | DeepSeek-V3 / Qwen3 | 需要精确提取责任人、时间等实体 |

一期 PoC 全部用 DeepSeek API（便宜、国内合规），后续可将分类任务下沉到本地小模型。

### 2.3 钉钉集成

| 用途 | 方式 |
|------|------|
| 创建待办 | 钉钉开放平台 API `topapi/workrecord/add` |
| 发送消息 | 钉钉机器人 Webhook / 工作通知 |
| 组织架构 | 钉钉通讯录 API 获取部门/人员信息 |

---

## 3. 验证链路设计

```
原始文件（PDF/Word/图片）
    │
    ▼
┌─────────────────────────────┐
│  Step 1: 文档解析             │
│  MinerU / PaddleOCR          │
│  输出: Markdown + 表格JSON    │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Step 2: 结构化提取           │
│  LLM (DeepSeek)              │
│  输出: 结构化 JSON            │
│  {                           │
│    "主题": "...",            │
│    "品牌": "长城",            │
│    "车型": ["哈弗H6", ...],   │
│    "生效时间": "...",         │
│    "截止时间": "...",         │
│    "返利规则": {...},         │
│    "考核口径": {...},         │
│    "风险条款": [...],         │
│    "约束条款": [...]          │
│  }                           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Step 3: 自动分类             │
│  LLM + 规则兜底               │
│  输出: 分类标签               │
│  {                           │
│    "业务类型": "发布类",       │
│    "业务域": ["销售", "售后"], │
│    "品牌": "长城"             │
│  }                           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Step 4: 待办提取             │
│  LLM (DeepSeek)              │
│  输出: 待办列表               │
│  [{                          │
│    "动作": "提交XX申报表",    │
│    "责任部门": "销售部",      │
│    "责任人": "张XX",          │
│    "截止时间": "2026-06-30",  │
│    "需提交材料": ["XX表",..], │
│    "来源文件": "长城Q2政策.pdf"│
│  }]                          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Step 5: 触发钉钉待办         │
│  钉钉 Open API               │
│  验证: 钉钉中出现待办卡片     │
└─────────────────────────────┘
```

---

## 4. 测试用例（至少准备 6 份真实文件）

| 编号 | 文件类型 | 难度特征 | 验证重点 |
|:---:|---------|---------|---------|
| T1 | 电子版 PDF | 纯文本 + 简单表格 | 基准准确率 |
| T2 | 电子版 PDF | 多栏排版 + 嵌套表格 | 布局解析 |
| T3 | 扫描件 PDF | 图片型 + 公章/水印 | OCR 抗干扰 |
| T4 | Word | 含批注/修订痕迹 | docx 解析完整性 |
| T5 | 图片 JPG | 拍照件，倾斜、光线不均 | OCR 鲁棒性 |
| T6 | 电子版 PDF | 20 页以上长文档 | 长文本上下文保持 |

---

## 5. 成功标准

每个 Step 的量化验收指标：

| 环节 | 指标 | 及格线 | 目标 |
|------|------|:---:|:---:|
| 文档解析 | 文本提取完整率 | ≥90% | ≥95% |
| 文档解析 | 表格还原准确率 | ≥85% | ≥90% |
| 结构化提取 | 关键字段提取准确率（主题/品牌/时间/车型） | ≥90% | ≥95% |
| 结构化提取 | 返利/考核规则提取完整性 | ≥80% | ≥85% |
| 自动分类 | 业务类型分类准确率 | ≥90% | ≥95% |
| 自动分类 | 业务域标签准确率 | ≥85% | ≥90% |
| 待办提取 | 待办项召回率 | ≥85% | ≥90% |
| 待办提取 | 责任人/截止时间准确率 | ≥90% | ≥95% |

**准出条件**：全部指标达到及格线，且 T3（扫描件）和 T5（拍照件）通过。

---

## 6. 两周执行计划

### 第 1 周

| 天 | 任务 | 产出 |
|:---:|------|------|
| 1 | 搭建 MinerU + PaddleOCR 环境，跑通 T1 | 环境就绪，基准解析结果 |
| 2 | 测试 T2-T5 全部文件类型，调优解析参数 | 解析层测试报告 |
| 3 | 编写结构化提取 Prompt，用 DeepSeek API 跑 T1-T3 | 结构化 JSON 输出 |
| 4 | 编写分类 + 待办提取 Prompt，端到端走通 T1 | 端到端 Demo 脚本 |
| 5 | 全量测试 T1-T6，记录各环节准确率 | PoC 测试数据 |

### 第 2 周

| 天 | 任务 | 产出 |
|:---:|------|------|
| 6 | 针对失败 case 优化 Prompt 和解析参数 | 优化后的准确率 |
| 7 | 集成钉钉待办 API，创建真实待办 | 钉钉待办截图 |
| 8 | 编写 PoC 总结报告（准确率、失败分析、成本测算） | 报告 |
| 9 | 准备演示：3 份文件端到端实时跑通 | 演示脚本 |
| 10 | 复盘 + 输出二期建议 | 二期技术方案 |

---

## 7. 成本预估

### PoC 阶段（2 周）

| 项目 | 费用 |
|------|------|
| DeepSeek API（测试 500 次调用，平均 10K token/次） | **≈ 50-100 元** |
| 服务器（已有或租用 4C8G 云服务器 2 周） | **≈ 200 元** |
| 钉钉开发者账号 | **免费** |
| **合计** | **≈ 300 元** |

### 生产环境预估（月度）

| 项目 | 配置 | 月费 |
|------|------|------|
| 本地服务器（文档解析 + 向量库） | 8C16G + 可选 GPU | ≈ 500-1500 元（已有则 0） |
| LLM API（月处理 1000 份文档） | DeepSeek / 通义千问 | ≈ 500-2000 元 |
| 钉钉 API | 免费 | 0 |
| **合计** | | **≈ 1000-3500 元/月** |

---

## 8. 风险预案

| 风险 | 概率 | 应对 |
|------|:---:|------|
| 扫描件 OCR 准确率低 | 中 | 先用电子版 PDF 跑通，扫描件加预处理（去噪/纠偏/超分） |
| 表格提取混乱 | 高 | MinerU 表格模型针对微调，或退化为截图 + 多模态模型 |
| LLM 结构化输出不稳定 | 低 | 加 JSON Schema 约束（DeepSeek 支持），加正则兜底 |
| 政策文件术语 LLM 不理解 | 中 | Prompt 中注入品牌/行业术语表（Few-shot + Glossary） |
| 长文档超出 context | 低 | 分段提取 + 合并去重，关键信息很少跨页 |

---

# 第三部分：PoC 代码实现

## 目录结构

```
poc/
├── pipeline.py              # 主流程：解析→提取→分类→待办，一键跑通
├── parse.py                 # 文档解析（PDF/Word/图片 → Markdown）
├── llm_client.py            # LLM 客户端（DeepSeek API，自动重试+JSON解析）
├── dingtalk_push.py         # 钉钉集成（待办创建/群消息/工作通知）
├── prompts/
│   ├── extract.md           # 结构化提取 Prompt
│   ├── classify.md          # 三维分类 Prompt
│   └── todo.md              # 待办提取 Prompt
├── samples/                 # 测试文件（待客户提供）
├── output/                  # 每步输出结果自动保存
└── requirements.txt
```

## 使用方式

```bash
# 1. 安装依赖
pip install -r poc/requirements.txt

# 2. 设置 API Key
export DEEPSEEK_API_KEY="sk-xxx"

# 3. 把真实政策文件放到 samples/ 目录

# 4. 跑管线
python poc/pipeline.py poc/samples/

# 或单文件
python poc/pipeline.py poc/samples/长城Q2政策.pdf

# 5.（可选）接钉钉
export DINGTALK_APP_KEY="xxx"
export DINGTALK_APP_SECRET="xxx"
export DINGTALK_AGENT_ID="xxx"
python poc/dingtalk_push.py
```

---

## requirements.txt

```txt
# 核心依赖
openai>=1.0.0          # DeepSeek 兼容 OpenAI SDK
PyMuPDF>=1.24.0        # PDF 解析（电子版）
python-docx>=1.1.0     # Word 解析
Pillow>=10.0.0         # 图片处理
requests>=2.31.0       # HTTP 请求（钉钉 API）

# OCR 依赖（扫描件/图片型 PDF 需要）
# 安装 PaddleOCR 前请参考: https://github.com/PaddlePaddle/PaddleOCR
# paddleocr>=2.8.0
# paddlepaddle>=2.6.0

# 可选：更好的 PDF 表格提取
# pdfplumber>=0.11.0

# 可选：钉钉加密消息
# pycryptodome>=3.20.0
```

---

## pipeline.py — 主流程脚本

```python
"""
政策文档智能处理 PoC 管线
串联：文档解析 → 结构化提取 → 自动分类 → 待办提取

用法:
  python pipeline.py <样本目录或单文件>

示例:
  python pipeline.py samples/长诚Q2返利政策.pdf
  python pipeline.py samples/        # 处理整个目录
"""

import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from parse import parse_file
from llm_client import run_step


def process_one(filepath: str, output_dir: str, config: dict = None) -> dict:
    """处理单个文件：解析 → 提取 → 分类 → 待办。返回完整结果。"""
    filename = Path(filepath).name
    print(f"\n{'='*60}")
    print(f"处理文件: {filename}")
    print(f"{'='*60}")

    # Step 1: 文档解析
    print("\n[1/4] 文档解析...")
    start = time.time()
    parsed = parse_file(filepath)
    elapsed = time.time() - start
    print(f"  解析完成 ({elapsed:.1f}s) | {parsed['char_count']} 字符 | 类型: {parsed['file_type']}")

    full_text = parsed["text"]
    if len(full_text) < 50:
        print(f"  警告: 提取文本过短，请检查文件内容或 OCR 环境")

    base_name = Path(filepath).stem
    os.makedirs(output_dir, exist_ok=True)
    _save_output(output_dir, f"{base_name}_01_parsed.md", full_text)

    # Step 2: 结构化提取
    print("\n[2/4] 结构化提取...")
    extract_result = run_step("结构化提取", "extract", full_text, config)
    _save_output(output_dir, f"{base_name}_02_extract.json", extract_result)
    print(f"  主题: {extract_result.get('主题', 'N/A')}")

    # Step 3: 自动分类
    print("\n[3/4] 自动分类...")
    summary = json.dumps(extract_result, ensure_ascii=False, indent=2)
    classify_result = run_step("自动分类", "classify",
        f"## 文档基本信息\n- 文件名: {filename}\n\n## 结构化摘要\n{summary}", config)
    _save_output(output_dir, f"{base_name}_03_classify.json", classify_result)
    print(f"  业务类型: {classify_result.get('业务类型', 'N/A')}")
    print(f"  业务域: {', '.join(classify_result.get('业务域', []))}")

    # Step 4: 待办提取
    print("\n[4/4] 待办提取...")
    doc_for_todo = f"## 文档文件名\n{filename}\n\n## 结构化摘要\n{summary}\n\n## 文档全文\n{full_text}"
    todo_result = run_step("待办提取", "todo", doc_for_todo, config)
    _save_output(output_dir, f"{base_name}_04_todos.json", todo_result)
    print(f"  提取待办: {len(todo_result)} 项")

    result = {
        "file": filename,
        "parsed": {"char_count": parsed["char_count"], "file_type": parsed["file_type"]},
        "extract": extract_result,
        "classify": classify_result,
        "todos": todo_result,
    }

    _save_output(output_dir, f"{base_name}_full_result.json", result)
    return result


def _save_output(output_dir: str, filename: str, data):
    path = os.path.join(output_dir, filename)
    if isinstance(data, str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def print_summary(results: list):
    print(f"\n\n{'='*60}")
    print(f"处理完毕 - 共 {len(results)} 个文件")
    print(f"{'='*60}")

    for r in results:
        print(f"\n{r['file']}")
        print(f"   主题: {r['extract'].get('主题', 'N/A')}")
        print(f"   分类: {r['classify'].get('业务类型', 'N/A')} | {', '.join(r['classify'].get('业务域', []))}")
        print(f"   待办: {len(r['todos'])} 项")
        for todo in r["todos"]:
            print(f"     - [{todo.get('优先级', '中')}] {todo.get('待办标题', '')} | 截止: {todo.get('截止时间', '')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(__file__), "output")

    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        supported = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
        files = sorted([
            os.path.join(target, f) for f in os.listdir(target)
            if Path(f).suffix.lower() in supported
        ])
        if not files:
            print(f"错误: {target} 目录下未找到支持的文件（PDF/DOCX/图片）")
            sys.exit(1)
    else:
        print(f"错误: {target} 不存在")
        sys.exit(1)

    print(f"找到 {len(files)} 个文件待处理")
    _ = input("按 Enter 开始处理...")

    config = {}

    results = []
    for filepath in files:
        try:
            result = process_one(filepath, output_dir, config)
            results.append(result)
        except Exception as e:
            print(f"\n处理失败: {filepath}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_summary(results)
        print(f"\n完整结果已保存至: {output_dir}")
```

---

## parse.py — 文档解析模块

```python
"""
文档解析模块：PDF/Word/图片 → Markdown 文本
依赖: pip install pymupdf python-docx pillow
OCR 可选: pip install paddleocr (扫描件必须)
"""

import os
import sys
from pathlib import Path

def parse_pdf(filepath: str) -> str:
    """解析 PDF，返回 Markdown 文本。优先用 PyMuPDF 提取文本，失败则走 OCR。"""
    import fitz  # PyMuPDF

    doc = fitz.open(filepath)
    texts = []
    for page in doc:
        text = page.get_text(sort=True)
        if text.strip():
            texts.append(text)
        else:
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            texts.append(_ocr_image_bytes(img_bytes))

    result = "\n\n".join(texts)
    if not result.strip():
        raise ValueError(f"未能从 PDF 提取任何文本: {filepath}")
    return result


def parse_docx(filepath: str) -> str:
    """解析 Word 文档，提取段落和表格。"""
    from docx import Document

    doc = Document(filepath)
    parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            style = para.style.name if para.style else ""
            if "Heading" in style or "heading" in style or "标题" in style:
                parts.append(f"## {para.text.strip()}")
            else:
                parts.append(para.text.strip())

    for i, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        if rows:
            header_sep = "|" + "|".join(["---"] * len(table.rows[0].cells)) + "|"
            rows.insert(1, header_sep)
            parts.append("\n".join(rows))

    result = "\n\n".join(parts)
    if not result.strip():
        raise ValueError(f"未能从 Word 提取任何文本: {filepath}")
    return result


def parse_image(filepath: str) -> str:
    """OCR 识别图片中的文字。"""
    from PIL import Image

    img = Image.open(filepath)
    return _ocr_image(img)


def parse_file(filepath: str) -> dict:
    """
    入口函数：根据文件扩展名自动选择解析器。
    返回 {"text": str, "file_type": str, "filename": str, "char_count": int}
    """
    ext = Path(filepath).suffix.lower()
    path = str(filepath)

    parsers = {
        ".pdf": parse_pdf,
        ".docx": parse_docx,
        ".doc": parse_docx,
        ".png": parse_image,
        ".jpg": parse_image,
        ".jpeg": parse_image,
        ".bmp": parse_image,
        ".tiff": parse_image,
    }

    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"不支持的文件格式: {ext}")

    text = parser(path)
    return {
        "text": text,
        "file_type": ext,
        "filename": Path(filepath).name,
        "char_count": len(text),
    }


def _ocr_image_bytes(img_bytes: bytes) -> str:
    """对图片字节进行 OCR。需要 PaddleOCR。"""
    try:
        from paddleocr import PaddleOCR
        import numpy as np
        from PIL import Image
        import io

        ocr = PaddleOCR(lang="ch", show_log=False)
        img = Image.open(io.BytesIO(img_bytes))
        img_np = np.array(img)
        results = ocr.ocr(img_np)
        if not results or not results[0]:
            return ""
        lines = []
        for line in results[0]:
            text = line[1][0]
            lines.append(text)
        return "\n".join(lines)
    except ImportError:
        print("PaddleOCR 未安装，返回空文本。安装: pip install paddleocr", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"OCR 失败: {e}", file=sys.stderr)
        return ""


def _ocr_image(img) -> str:
    """对 PIL Image 进行 OCR。需要 PaddleOCR。"""
    try:
        from paddleocr import PaddleOCR
        import numpy as np

        ocr = PaddleOCR(lang="ch", show_log=False)
        img_np = np.array(img)
        results = ocr.ocr(img_np)
        if not results or not results[0]:
            return ""
        return "\n".join(line[1][0] for line in results[0])
    except ImportError:
        print("PaddleOCR 未安装。安装: pip install paddleocr", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"OCR 失败: {e}", file=sys.stderr)
        return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <文件路径>")
        sys.exit(1)

    result = parse_file(sys.argv[1])
    print(f"文件: {result['filename']}")
    print(f"类型: {result['file_type']}")
    print(f"字符数: {result['char_count']}")
    print(f"\n{'='*60}\n")
    print(result["text"][:2000])
```

---

## llm_client.py — LLM 客户端

```python
"""
LLM 客户端：统一封装 DeepSeek API 调用。
支持 OpenAI 兼容接口，可切换为通义千问、智谱等。
"""

import os
import json
import re
import time
from pathlib import Path

import openai

DEFAULT_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    "api_key": os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
}


def load_prompt(name: str) -> str:
    """加载 prompts/ 目录下的 Prompt 模板。"""
    prompt_dir = Path(__file__).parent / "prompts"
    path = prompt_dir / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def call_llm(prompt: str, config: dict = None) -> str:
    """
    调用 LLM，返回文本响应。
    支持自动重试（最多 3 次），处理 rate limit 和 server error。
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    if not cfg["api_key"]:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY 或 LLM_API_KEY")

    client = openai.OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=cfg["model"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except openai.RateLimitError:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise
        except openai.APIError as e:
            if attempt < max_retries - 1 and e.status_code and e.status_code >= 500:
                wait = 2 ** (attempt + 1)
                print(f"  Server error, {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise


def extract_json(text: str) -> dict | list:
    """从 LLM 响应中提取 JSON。容忍 markdown 代码块包裹。"""
    text = text.strip()

    # 移除 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 正则提取第一个 JSON 对象或数组
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从响应中解析 JSON:\n{text[:500]}")


def run_step(step_name: str, prompt_name: str, doc_text: str, config: dict = None) -> dict | list:
    """
    执行一个完整的 LLM 步骤：加载 Prompt → 拼接文档 → 调用 LLM → 解析 JSON
    返回解析后的 JSON 对象（dict 或 list）。
    """
    prompt = load_prompt(prompt_name)
    full_prompt = f"{prompt}\n\n{doc_text}"

    # 截断超长文本（DeepSeek 上下文 64K，留够余量）
    max_input = 50000
    if len(full_prompt) > max_input:
        full_prompt = full_prompt[:max_input]
        print(f"  文档过长，已截断至 {max_input} 字符")

    print(f"  -> 调用 LLM ({prompt_name})...")
    start = time.time()
    response = call_llm(full_prompt, config)
    elapsed = time.time() - start

    result = extract_json(response)
    print(f"  {step_name} 完成 ({elapsed:.1f}s)")
    return result
```

---

## dingtalk_push.py — 钉钉集成模块

```python
"""
钉钉集成模块：创建待办、发送消息。
依赖: pip install requests
钉钉开放平台文档: https://open.dingtalk.com/
"""

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse

import requests


class DingTalkClient:
    """
    钉钉 API 客户端。

    环境变量:
      DINGTALK_APP_KEY     - 应用 AppKey
      DINGTALK_APP_SECRET  - 应用 AppSecret
      DINGTALK_AGENT_ID    - 应用 AgentId
      DINGTALK_ROBOT_TOKEN - 机器人 Webhook Token（发消息用，可选）
    """

    def __init__(self):
        self.app_key = os.getenv("DINGTALK_APP_KEY", "")
        self.app_secret = os.getenv("DINGTALK_APP_SECRET", "")
        self.agent_id = os.getenv("DINGTALK_AGENT_ID", "")
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """获取钉钉 access_token，自动缓存。"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = "https://oapi.dingtalk.com/gettoken"
        params = {"appkey": self.app_key, "appsecret": self.app_secret}
        resp = requests.get(url, params=params)
        data = resp.json()

        if data.get("errcode") != 0:
            raise RuntimeError(f"获取钉钉 access_token 失败: {data}")

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"] - 60
        return self._access_token

    def create_todo(self, todo_item: dict, user_id: str) -> dict:
        """
        创建钉钉待办。

        todo_item 格式（来自待办提取的输出）:
          {
            "待办标题": "...",
            "详细说明": "...",
            "截止时间": "YYYY-MM-DD",
            "优先级": "高 | 中 | 低",
            ...
          }

        user_id: 钉钉用户 ID（可通过通讯录 API 获取）
        """
        token = self._get_access_token()
        url = "https://oapi.dingtalk.com/topapi/workrecord/add"

        body = {
            "userid": user_id,
            "create_time": int(time.time() * 1000),
            "title": todo_item.get("待办标题", "待办事项"),
            "url": "",
            "formItemList": [
                {"title": "详细说明", "content": todo_item.get("详细说明", "")},
                {"title": "优先级", "content": todo_item.get("优先级", "中")},
                {"title": "截止时间", "content": todo_item.get("截止时间", "")},
                {"title": "来源", "content": todo_item.get("关联来源", "")},
            ],
        }

        resp = requests.post(
            url,
            params={"access_token": token},
            json=body,
        )
        return resp.json()

    def send_group_message(self, content: str, robot_token: str = None) -> dict:
        """
        通过钉钉机器人发送群消息（Markdown 格式）。
        """
        token = robot_token or os.getenv("DINGTALK_ROBOT_TOKEN", "")
        if not token:
            raise ValueError("请设置 DINGTALK_ROBOT_TOKEN 环境变量")

        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": "政策文档分析通知",
                "text": content,
            },
        }

        resp = requests.post(url, json=body)
        return resp.json()

    def send_work_notice(self, user_id: str, content: str) -> dict:
        """通过工作通知发送消息给指定用户。"""
        token = self._get_access_token()
        url = f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"

        body = {
            "agent_id": int(self.agent_id),
            "userid_list": user_id,
            "msg": {
                "msgtype": "markdown",
                "markdown": {
                    "title": "政策文档分析通知",
                    "text": content,
                },
            },
        }

        resp = requests.post(
            url,
            params={"access_token": token},
            json=body,
        )
        return resp.json()

    def get_user_by_mobile(self, mobile: str) -> str:
        """根据手机号获取钉钉用户 ID。"""
        token = self._get_access_token()
        url = "https://oapi.dingtalk.com/topapi/v2/user/getbymobile"
        resp = requests.post(
            url,
            params={"access_token": token},
            json={"mobile": mobile},
        )
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"获取钉钉用户失败: {data}")
        return data["result"]["userid"]


def format_todos_as_markdown(todos: list, source_file: str) -> str:
    """将待办列表格式化为钉钉 Markdown 消息。"""
    lines = [
        f"## 政策文件分析 - {source_file}",
        "",
    ]

    for i, todo in enumerate(todos, 1):
        priority_emoji = {"高": "RED", "中": "YELLOW", "低": "GREEN"}.get(todo.get("优先级", "中"), "WHITE")
        lines.extend([
            f"---",
            f"### {priority_emoji} 待办 {i}：{todo.get('待办标题', '')}",
            f"",
            f"**详细说明**：{todo.get('详细说明', '')}",
            f"**责任部门**：{todo.get('责任部门', '')}  ",
            f"**责任人角色**：{todo.get('责任人角色', '')}  ",
            f"**截止时间**：{todo.get('截止时间', '')}  ",
            f"**需提交材料**：{'、'.join(todo.get('需提交材料', []))}",
            f"**关联来源**：{todo.get('关联来源', '')}",
            f"",
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    client = DingTalkClient()
    test_todo = {
        "待办标题": "提交Q2返利申报表",
        "详细说明": "请各门店于7月5日前完成Q2返利数据填报并上传至财务系统。",
        "截止时间": "2026-07-05",
        "优先级": "高",
        "关联来源": "长城Q2返利政策.pdf - 第3条",
    }

    try:
        result = client.create_todo(test_todo, user_id="test_user")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"钉钉 API 调用失败（预期内，需配置环境变量）: {e}")
        print("配置方法: 设置 DINGTALK_APP_KEY, DINGTALK_APP_SECRET, DINGTALK_AGENT_ID")
```

---

## Prompt 模板

### prompts/extract.md — 结构化提取

```markdown
# 角色
你是一个汽车行业政策文件分析专家，专注于从厂商政策文件中提取结构化信息。

# 输入
下面是经过文档解析后的政策文件内容（Markdown 格式）。内容可能包含 OCR 识别误差，请结合上下文修正明显错误。

# 提取要求
从文档中提取以下字段。如果文档中不存在对应信息，则填 null（字符串类型）或 []（数组类型）。

## 字段说明

1. **主题**：一句话概括政策核心内容，不超过 50 字
2. **适用品牌**：从 [长城, 奇瑞, 华为, 其他] 中选择，多个用数组
3. **适用车型**：列出所有涉及的车型名称，如 ["哈弗H6", "坦克300"]
4. **生效时间**：YYYY-MM-DD 格式
5. **截止时间**：YYYY-MM-DD 格式，如无明确截止时间则填 null
6. **返利规则**：逐条列出，每条包含 {条件, 比例/金额, 上限}
7. **考核口径**：逐条列出，每条包含 {指标, 目标值, 考核周期}
8. **风险提示**：列出所有风险、整改、处罚相关条款，每条为字符串
9. **约束条款**：除风险外的其他硬性要求和限制条件，每条为字符串
10. **奖惩要求**：奖励和惩罚的具体条款，每条为字符串
11. **对接部门**：文件中提到的对接/负责部门
12. **附件要求**：需要提交的材料、表格、证明文件等

# 输出格式
严格按以下 JSON 格式输出。不要输出任何 JSON 之外的内容，不要用 markdown 代码块包裹。

{
  "主题": "string",
  "适用品牌": ["string"],
  "适用车型": ["string"],
  "生效时间": "YYYY-MM-DD",
  "截止时间": "YYYY-MM-DD | null",
  "返利规则": [{"条件": "string", "比例或金额": "string", "上限": "string"}],
  "考核口径": [{"指标": "string", "目标值": "string", "考核周期": "string"}],
  "风险提示": ["string"],
  "约束条款": ["string"],
  "奖惩要求": ["string"],
  "对接部门": ["string"],
  "附件要求": ["string"]
}

# 注意事项
- 不要编造文档中不存在的信息
- OCR 识别的明显错字请根据上下文修正（如 "哈弟H6" → "哈弗H6"）
- 金额、比例等数字务必保留原文精度
- 时间统一为 YYYY-MM-DD，原文只有月份则补 01 日

# 文档内容
```

### prompts/classify.md — 自动分类

```markdown
# 角色
你是一个汽车经销商集团的政策文件分类专家。

# 输入
下面是一份政策文件的结构化摘要，包含主题、品牌、业务内容等信息。

# 分类维度
你需要从以下三个维度对文档进行分类：

## 维度1：业务类型
- **发布类**：新政策发布、新规则出台、新标准制定
- **过程类**：执行通知、操作指引、流程说明、申报通知
- **通报类**：考核结果通报、奖惩公告、整改通知、风险警示

## 维度2：业务域（可多选）
- **销售**：销量目标、销售政策、展厅管理、客户权益
- **财务**：返利、结算、开票、对账、费用报销
- **保险**：保险产品、续保政策、理赔流程
- **售后**：维修保养、配件管理、三包索赔、服务标准
- **人力**：人员编制、绩效考核、培训认证
- **物流**：车辆调拨、运输、库存管理
- **精品**：改装、精品附件、加装业务
- **二手车**：置换、评估、二手车销售

## 维度3：品牌
- 长城 / 奇瑞 / 华为 / 多品牌

# 输出格式
严格按以下 JSON 格式输出。不要输出任何 JSON 之外的内容。

{
  "业务类型": "发布类 | 过程类 | 通报类",
  "业务域": ["string"],
  "品牌": ["string"],
  "分类依据": "一句话说明为何如此分类",
  "推送范围": {
    "部门": ["string"],
    "建议角色": ["string"]
  }
}

# 分类依据说明（关键）
- 如果文档标题或首段明确出现"关于发布""关于印发""通知""公告"等字样，以此为准
- 如果文档包含考核结果、排名、处罚决定，归类为"通报类"
- 如果文档给出具体执行步骤、操作要求、材料提交流程，归类为"过程类"
- 业务域根据文档涉及的实际业务内容判断，不要根据"可能相关"猜测

# 文档结构化摘要
```

### prompts/todo.md — 待办提取

```markdown
# 角色
你是一个汽车经销商集团的运营管理专家，负责从政策文件中精准提取可执行的待办事项。

# 输入
下面是一份政策文件的完整内容和结构化摘要。

# 提取要求
从文档中提取所有需要相关人员/部门执行的具体动作。每一项待办必须满足：**有明确执行者、有明确动作、有时间节点**。

## 每条待办包含

1. **待办标题**：简洁的动作描述，不超过 30 字，动词开头。如 "提交Q2返利申报表"
2. **详细说明**：补充待办的具体要求、标准和注意事项，不超过 200 字
3. **责任部门**：负责执行的部门
4. **责任人角色**：如 "销售经理""财务主管""门店店长"，不填具体姓名
5. **截止时间**：YYYY-MM-DD 格式。如原文只提及"月底前""5个工作日内"，请根据生效时间推算
6. **优先级**：高 / 中 / 低
   - **高**：涉及罚款、整改、考核不达标、有明确 deadline 且逾期有处罚
   - **中**：常规申报、数据提交、有 deadline 但无明确处罚
   - **低**：知晓性事项、无明确 deadline
7. **需提交材料**：需要提交的文件、表格、证明材料列表
8. **反馈要求**：提交方式、审批流程、抄送对象等
9. **关联来源**：来源文件名，标注具体的段落或条款编号

# 优先级判定规则
- 出现"逾期不补""逾期作废""罚款""扣分""整改""警告""取消资格" → 高
- 出现"务必""必须""确保""按时提交"但无明确处罚 → 中
- 出现"请知悉""仅供参考""建议" → 低

# 输出格式
严格按以下 JSON 格式输出。不要输出任何 JSON 之外的内容。如无待办项，返回空数组。

[
  {
    "待办标题": "string",
    "详细说明": "string",
    "责任部门": "string",
    "责任人角色": "string",
    "截止时间": "YYYY-MM-DD",
    "优先级": "高 | 中 | 低",
    "需提交材料": ["string"],
    "反馈要求": "string",
    "关联来源": "string"
  }
]

# 注意事项
- 已过期的时间节点也要提取，标注原文时间
- 反复出现的同类待办去重合并
- 不要将"政策条款本身"提取为待办，只提取需要人执行的**动作**

# 文档内容
```

---

# 附录：钉钉配置说明

1. 登录 [钉钉开放平台](https://open.dingtalk.com/)
2. 创建企业内部应用 → 获取 AppKey、AppSecret、AgentId
3. 配置应用权限：待办、工作通知、通讯录读取
4. 设置环境变量：

```bash
export DINGTALK_APP_KEY="dingxxx"
export DINGTALK_APP_SECRET="xxx"
export DINGTALK_AGENT_ID="123456"
export DINGTALK_ROBOT_TOKEN="xxx"  # 可选，用于群消息
```
