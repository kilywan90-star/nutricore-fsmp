import tempfile
import os
import yaml
from agent_security_detector.rule_manager.rule_loader import RuleLoader

def test_rule_loader_initialization():
    loader = RuleLoader()
    assert len(loader.rules) == 0

def test_load_from_file():
    loader = RuleLoader()

    # 创建临时规则文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "plugin": "sensitive_info",
            "config": {
                "custom_patterns": {
                    "test": "test\\d+"
                },
                "detect_types": ["phone", "email"]
            }
        }, f)
        temp_file = f.name

    try:
        loader.load_from_file(temp_file)
        assert "sensitive_info" in loader.rules
        assert loader.rules["sensitive_info"]["custom_patterns"]["test"] == "test\\d+"
        assert loader.rules["sensitive_info"]["detect_types"] == ["phone", "email"]
    finally:
        os.unlink(temp_file)

def test_load_from_dir():
    loader = RuleLoader()

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建规则文件1
        with open(os.path.join(temp_dir, "rule1.yaml"), 'w') as f:
            yaml.dump({
                "plugin": "plugin1",
                "config": {"key1": "value1"}
            }, f)

        # 创建规则文件2
        with open(os.path.join(temp_dir, "rule2.yaml"), 'w') as f:
            yaml.dump({
                "plugin": "plugin2",
                "config": {"key2": "value2"}
            }, f)

        # 加载目录
        loader.load_from_dir(temp_dir)

        assert "plugin1" in loader.rules
        assert "plugin2" in loader.rules
        assert loader.rules["plugin1"]["key1"] == "value1"
        assert loader.rules["plugin2"]["key2"] == "value2"
```
