import subprocess
import json
import tempfile

def test_cli_help():
    """测试CLI帮助命令"""
    result = subprocess.run(["python", "-m", "agent_security_detector.adapters.cli.main", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "detect" in result.stdout

def test_cli_detect_command():
    """测试CLI检测命令"""
    # 创建临时输入文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "prompt": "test",
            "response": "我的手机号是13812345678",
            "tool_calls": []
        }, f)
        input_file = f.name

    try:
        # 运行CLI检测
        result = subprocess.run(
            ["python", "-m", "agent_security_detector.adapters.cli.main", "detect", "--input", input_file, "--output-format", "json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1  # 检测到风险应该返回非零
        output = json.loads(result.stdout)
        assert output["has_risk"] is True
        assert len(output["results"]) > 0
        assert any(r["risk_type"] == "sensitive_information" for r in output["results"])
    finally:
        import os
        os.unlink(input_file)
```
