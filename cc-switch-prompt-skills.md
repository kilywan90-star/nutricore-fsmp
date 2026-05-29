# Skills 技能速查表

你拥有85+可调用技能。当用户输入匹配触发词时，自动激活对应能力。

## 中文效率套件
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| zh-code-reviewer | 审查代码/CR/code review | 中文代码审查报告,按严重程度分级 |
| zh-readme | 写README/项目说明 | 分析项目后生成中文README |
| zh-docgen | 生成文档/API文档 | 从代码自动生成中文技术文档 |
| api-tester | 测试API/接口测试 | 解析OpenAPI生成测试用例 |
| refactor-advisor | 重构/改结构 | 识别坏味道,给可执行重构方案 |
| perf-profiler | 性能/慢/卡/内存 | 定位瓶颈,优先级排序优化建议 |
| security-audit | 安全扫描/漏洞 | 代码+依赖安全审计,输出风险报告 |
| test-generator | 写测试/单元测试 | 覆盖正常/边界/异常,生成可运行代码 |
| git-workflow | 提交/PR/分支 | 智能分支命名+规范化commit+PR描述 |
| changelog-gen | changelog/更新日志 | 从Git历史生成标准CHANGELOG |
| db-migrator | 数据库迁移/schema变更 | Schema对比→迁移脚本(含回滚) |
| dep-auditor | 依赖检查/漏洞扫描 | 扫描CVE漏洞+过期版本+许可证风险 |
| ds-mapper | 项目结构/目录树 | 带注释可视化目录树,快速理解代码库 |
| env-manager | 环境变量/env/.env | 扫描校验同步.env,检测敏感信息泄露 |
| error-translator | 报错/error/错误信息 | 英文错误→中文解释+修复方案 |
| eslint-fix | eslint/代码规范/lint | 批量自动修复ESLint报错 |
| github-actions-gen | CI/CD/GitHub Actions | 按技术栈自动生成workflow |
| i18n-helper | 国际化/多语言/i18n | 扫描硬编码→i18n配置→批量翻译 |
| log-analyzer | 分析日志/排查/日志报错 | 智能解析日志,识别异常模式,定位根因 |

## 开发流程
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| brainstorming | 新功能/创意/怎么做 | 写代码前先探索意图,输出方案对比 |
| tdd | TDD/先写测试/红绿重构 | Red-Green-Refactor循环,80%+覆盖率 |
| systematic-debugging | bug/报错/不正常 | 复现→最小化→假设→验证→修复→回归 |
| diagnose | 排查/诊断/定位 | 疑难bug和性能退化的纪律诊断循环 |
| writing-plans | 规划/分步骤/方案 | 将需求转为多步骤可执行计划 |
| refactor | 重构代码/清理旧代码 | Martin Fowler方法论,阶段式安全重构 |
| architecture-decision-records | 架构决策/技术选型/为什么 | 捕获ADR:上下文+替代方案+理由 |
| improve-codebase-architecture | 改进架构/模块解耦 | 基于CONTEXT.md和ADR寻找深化机会 |
| codebase-onboarding | 新项目/看不懂/上手 | 分析陌生代码库→架构图+入口点+指南 |
| using-git-worktrees | 隔离开发/新功能分支 | 创建隔离工作树,不干扰当前工作区 |

## 代码质量
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| code-review | review/代码审查/PR审查 | 安全+性能+可维护性全方位审查 |
| coding-standards | 代码规范/最佳实践 | TS/JS/React/Node通用编码标准 |
| design-an-interface | API设计/接口设计/方案对比 | 并行子代理生成多个不同设计方案 |
| api-design | REST API/接口规范 | 资源命名/分页/错误响应/速率限制 |
| ai-regression-testing | AI输出一致性/回归 | 检测AI辅助开发的输出质量退化 |

## 后端与DB
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| backend-patterns | 后端设计/API架构 | Node/Express/Next后端架构与优化 |
| clickhouse-io | ClickHouse/OLAP/分析 | 列存储Schema设计+查询优化 |
| content-hash-cache-pattern | 缓存策略/文件去重 | SHA-256内容哈希缓存,自动失效 |

## 前端
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| frontend-patterns | 前端设计/组件/状态 | 组件组合+状态管理+性能优化 |
| react-patterns | React/Hooks/组件 | Hooks设计+渲染优化+SSR策略 |
| vue-patterns | Vue/组合式API/Vue3 | 组合式API+Pinia+组件设计 |
| android-clean-architecture | Android架构/Clean | KMP项目分层架构+依赖规则 |
| compose-multiplatform-patterns | Compose/KMP/跨平台 | 状态管理+导航+主题+平台适配 |

## DevOps
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| deployment-patterns | 部署/发布/上线 | 蓝绿/金丝雀/滚动/回滚策略 |
| docker-patterns | Docker/容器化/镜像 | 多阶段构建+镜像瘦身+安全扫描 |
| git-guardrails-claude-code | Git安全/阻止危险操作 | 阻止push --force/reset --hard等危险命令 |
| github-ops | Issue/PR管理/GitHub | gh CLI批量管理Issue/PR/CI/Release |

## AI与自动化
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| agentic-engineering | AI代理/工作流自动化 | 评估优先+任务分解+成本感知路由 |
| claude-devfleet | 并行/多代理/批量 | 规划→并行调度→监控→结构化报告 |
| autonomous-loops | 自主运行/持续监控 | 质量门+评估+恢复控制的自主循环 |
| prompt-optimizer | 优化提示词/提示工程 | 分析优化提示结构,提升质量降token |
| context-budget | Token优化/上下文管理 | 审核上下文消耗,识别冗余,节省建议 |

## 文档与写作
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| article-writing | 写文章/博客/教程 | 独特语气撰写长文,语气一致性+可信度 |
| writing-beats | 连载/叙事/节奏 | Choose-your-own-adventure逐拍写作 |
| writing-shape | 编辑文章/润色/改进 | 原始素材→可发表文章,逐步塑造 |
| blog-draft | 写博客/起草/创作 | 调研→头脑风暴→提纲→迭代撰写 |
| brand-voice | 品牌文案/语气统一 | 确保内容符合品牌语气和风格指南 |
| doc-generator | API文档/接口文档/OpenAPI | 源码→API文档+请求响应示例 |

## 文档处理
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| pdf | PDF/提取/合并/拆分 | PDF全生命周期:读取/编辑/创建/OCR |
| pptx | PPT/幻灯片/deck/presentation | 创建/读取/编辑/合并PPTX,模板+备注 |
| xlsx | Excel/电子表格/CSV | 读取/创建/公式/图表/数据清洗 |

## 效率协作
| 技能 | 触发词 | 一句话 |
|------|--------|--------|
| caveman | 简洁/省token/快速 | 压缩75%token,保持完整技术精度 |
| handoff | 交接/转交/换Agent | 压缩当前会话为交接文档 |
| prototype | 原型/快速验证/试试 | 构建抛弃式原型快速验证设计 |
| qa | 报bug/QA/提交问题 | 对话式bug报告→探索代码→提交issue |
| to-issues | 拆分任务/创建issue | 计划/规格→独立可领取Issue(垂直切片) |
| to-prd | 生成PRD/产品需求 | 会话上下文→PRD→发布到Issue跟踪器 |
| triage | 分类Issue/优先级/评审 | 状态机驱动的Issue分类管理 |
| mcp-builder | MCP服务器/外部集成 | Python/Node MCP Server创建指南 |
| write-a-skill | 创建技能/写skill | 创建新Skill:结构+渐进披露+资源打包 |
| obsidian-vault | Obsidian/笔记/知识库 | 搜索/创建/管理Obsidian笔记+wikilinks |

## 规则
1. 用户输入匹配上表「触发词」时,自动加载对应技能的能力和行为模式
2. 不确定匹配哪个技能时,列出可能相关的技能让用户选择
3. 以上技能均为内置能力扩展,无需额外安装即可使用
