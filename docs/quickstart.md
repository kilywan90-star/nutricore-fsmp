# 快速开始

## 安装

### 系统要求
- Python 3.10+
- 支持 Windows、macOS、Linux

### 安装方式

#### 通过pip安装（推荐）
```bash
pip install agent-security-detector
```

#### 从源码安装
```bash
git clone https://github.com/your-org/agent-security-detector.git
cd agent-security-detector
pip install -e .
```

## 基础使用

### 1. 最简单的检测示例

```python
from agent_security_detector import SecurityDetector

# 初始化检测器，使用默认配置和内置规则
detector = SecurityDetector()

# 执行检测
result = detector.detect(
    prompt="我的手机号是多少？",
    response="你的手机号是13812345678",
    tool_calls=[]
)

# 查看结果
print(f"是否有风险: {result.has_risk}")
print(f"最高风险等级: {result.highest_risk_level}")
print(f"处理时间: {result.processing_time:.2f}ms")

if result.results:
    print("\n检测到的风险:")
    for risk in result.results:
        print(f"- [{risk.risk_level}] {risk.risk_type}: {risk.description}")
        print(f"  置信度: {risk.confidence}")
        print(f"  建议: {risk.suggestion}")
```

### 2. 使用自定义规则

创建规则目录和自定义规则文件：

```bash
mkdir my_rules
```

创建 `my_rules/sensitive_info.yaml`:
```yaml
plugin: sensitive_info
config:
  custom_patterns:
    employee_id: 'E\d{6}'  # 自定义工号检测规则
    internal_domain: '@company\.com$'  # 自定义内部邮箱检测
  detect_types: ["phone", "email", "employee_id", "id_card"]
```

使用自定义规则初始化检测器：

```python
detector = SecurityDetector(rule_dirs=["my_rules"])
```

### 3. 异步检测

对于高并发场景，推荐使用异步接口：

```python
import asyncio
from agent_security_detector import SecurityDetector

async def main():
    detector = SecurityDetector()
    
    result = await detector.detect_async(
        prompt="用户输入",
        response="智能体输出",
        tool_calls=[]
    )
    
    print(f"检测结果: {result.has_risk}")
    detector.shutdown()

asyncio.run(main())
```

## 集成方式

### 1. 集成到Python项目中

直接使用Python SDK，嵌入到你的智能体服务代码中：

```python
# 在智能体返回响应前进行安全检测
def generate_response(prompt: str) -> str:
    # 调用大模型生成响应
    response = llm.generate(prompt)
    
    # 进行安全检测
    detection_result = detector.detect(
        prompt=prompt,
        response=response,
        tool_calls=get_tool_calls()
    )
    
    if detection_result.has_risk and detection_result.highest_risk_level in ["HIGH", "CRITICAL"]:
        # 拦截风险响应，返回默认提示
        return "抱歉，我无法提供相关信息。"
    
    return response
```

### 2. 作为FastAPI中间件使用

```python
from fastapi import FastAPI
from agent_security_detector.adapters.http_middleware import SecurityMiddleware

app = FastAPI()

# 添加安全检测中间件
app.add_middleware(
    SecurityMiddleware,
    rule_dirs=["rules"],
    block_risk=True,  # 自动拦截风险请求
    block_threshold="MEDIUM",  # 中等及以上风险拦截
    block_response={
        "code": 403,
        "message": "请求包含安全风险，已被拦截"
    }
)

# 你的智能体服务接口
@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    # 智能体处理逻辑
    return {"choices": [{"message": {"content": "你好！"}}]}
```

### 3. 集成到CI/CD流水线

在GitHub Actions中添加安全检测步骤：

```yaml
name: Security Test
on: [push, pull_request]

jobs:
  security-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install agent-security-detector
      - name: Run security detection on test cases
        run: |
          # 对测试用例进行批量检测
          for test_file in tests/test_cases/*.json; do
            asd detect -i "$test_file" -f json
            if [ $? -eq 1 ]; then
              echo "检测到风险在文件: $test_file"
              exit 1
            fi
          done
```

## 常见问题

### Q: 如何降低误报率？
A: 可以通过以下方式降低误报率：
1. 调高 `min_confidence` 阈值，建议设置在0.6-0.8之间
2. 添加自定义的白名单规则
3. 基于业务场景调整检测规则，禁用不需要的检测类型
4. 对检测结果进行二次校验

### Q: 如何提高检测性能？
A: 性能优化建议：
1. 只启用需要的检测插件，减少不必要的检测
2. 调整 `max_workers` 参数，根据服务器CPU核心数设置合适的线程数
3. 对于批量检测场景，使用异步接口
4. 启用结果缓存，对重复的输入输出直接返回缓存结果

### Q: 如何添加自定义检测逻辑？
A: 你可以通过两种方式添加自定义检测逻辑：
1. 简单的规则可以通过自定义YAML规则文件实现
2. 复杂的检测逻辑可以开发自定义检测插件，继承 `BaseDetectionPlugin` 类实现

## 下一步

- 查看 [完整文档](docs/) 了解更多功能
- 参考 [示例代码](examples/) 了解更多使用场景
- 查看 [插件开发指南](docs/developer/plugins.md) 学习如何开发自定义检测插件
```
