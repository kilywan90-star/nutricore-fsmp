# Agent Security Detector

全面的AI智能体安全检测工具，提供多层级的安全防护能力。

## 功能特性

### 检测能力
- 🛡️ **内容安全检测**: 敏感信息（手机号、身份证、邮箱、银行卡等）泄露检测、有害内容检测
- 🚨 **行为安全检测**: 越权操作检测、危险操作检测、数据泄露检测
- 🔍 **工具调用安全检测**: SQL注入、命令注入、代码注入检测、API滥用检测
- 🎭 **对抗性输入检测**: 提示注入检测、越狱攻击检测、对抗样本检测

### 使用场景
- ✅ 开发阶段安全测试: 集成到CI/CD流水线，在开发阶段发现安全问题
- ⚡ 实时请求拦截: 作为中间件部署在智能体服务前，实时拦截风险请求
- 📊 批量安全审计: 对历史对话数据进行批量安全审计，发现潜在风险
- 📈 运行时安全监控: 对接监控系统，持续监控智能体运行安全状态

### 核心优势
- 🔌 **插件化架构**: 所有检测能力模块化，支持灵活扩展自定义检测规则
- ⚡ **高性能**: 异步并行检测，低延迟，不影响智能体服务性能
- 🎯 **高准确率**: 多层检测机制，结合规则和AI模型，降低误报率
- 🔧 **高度可配置**: 支持自定义规则、检测阈值、告警策略
- 🔗 **易于集成**: 提供Python SDK、HTTP中间件、CLI工具等多种集成方式

## 快速开始

### 安装

```bash
pip install agent-security-detector
```

### 基本使用

#### Python SDK

```python
from agent_security_detector import SecurityDetector

# 初始化检测器
detector = SecurityDetector(
    rule_dirs=["rules"]  # 加载自定义规则目录
)

# 执行检测
result = detector.detect(
    prompt="用户输入内容",
    response="智能体输出内容",
    tool_calls=[]  # 工具调用记录
)

# 处理检测结果
if result.has_risk:
    print(f"检测到风险，最高等级: {result.highest_risk_level}")
    for risk in result.results:
        print(f"- [{risk.risk_level}] {risk.risk_type}: {risk.description}")
else:
    print("未检测到风险")

# 异步接口
# result = await detector.detect_async(...)

# 关闭检测器
detector.shutdown()
```

#### 命令行工具

```bash
# 检测单个请求
echo '{"prompt": "用户输入", "response": "智能体输出"}' | asd detect -f json

# 从文件读取输入
asd detect -i input.json -o output.json

# 指定规则目录
asd detect -i input.json -r ./rules -f text
```

## 许可证

MIT License
```
