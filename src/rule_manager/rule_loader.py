import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

class RuleLoader:
    """规则加载器，负责从文件和目录加载检测规则"""

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}  # plugin_name -> config

    def load_from_file(self, file_path: str) -> None:
        """
        从单个文件加载规则
        :param file_path: 规则文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rule_config = yaml.safe_load(f)

            if not isinstance(rule_config, dict):
                raise ValueError(f"Invalid rule format in {file_path}: expected dict")

            plugin_name = rule_config.get("plugin")
            if not plugin_name:
                raise ValueError(f"Missing 'plugin' field in {file_path}")

            config = rule_config.get("config", {})
            if plugin_name in self.rules:
                # 合并配置
                self.rules[plugin_name].update(config)
            else:
                self.rules[plugin_name] = config

        except Exception as e:
            import logging
            logging.error(f"Failed to load rule from {file_path}: {str(e)}")
            raise

    def load_from_dir(self, dir_path: str) -> None:
        """
        从目录加载所有规则文件
        :param dir_path: 规则目录路径
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")

        # 支持的文件扩展名
        supported_extensions = ['.yaml', '.yml', '.json']

        for file_path in path.rglob('*'):
            if file_path.suffix.lower() in supported_extensions:
                self.load_from_file(str(file_path))

    def get_rule(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定插件的规则配置
        :param plugin_name: 插件名称
        :return: 规则配置，如果不存在返回None
        """
        return self.rules.get(plugin_name)

    def get_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有规则配置
        :return: 所有规则配置字典
        """
        return self.rules.copy()

    def clear(self) -> None:
        """清空所有加载的规则"""
        self.rules.clear()
```
