import asyncio
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult

class PluginScheduler:
    """插件调度器，负责管理和执行检测插件"""

    def __init__(self, max_workers: int = 10):
        """
        初始化调度器
        :param max_workers: 并行检测的最大线程数
        """
        self.plugins: Dict[str, BaseDetectionPlugin] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def register_plugin(self, plugin: BaseDetectionPlugin) -> None:
        """
        注册检测插件
        :param plugin: 检测插件实例
        """
        if plugin.name in self.plugins:
            raise ValueError(f"Plugin {plugin.name} already registered")
        self.plugins[plugin.name] = plugin

    def unregister_plugin(self, plugin_name: str) -> None:
        """
        注销检测插件
        :param plugin_name: 插件名称
        """
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]

    def get_plugin(self, plugin_name: str) -> Optional[BaseDetectionPlugin]:
        """
        获取注册的插件
        :param plugin_name: 插件名称
        :return: 插件实例，如果不存在返回None
        """
        return self.plugins.get(plugin_name)

    def run_sync(self, context: DetectionContext, plugin_names: Optional[List[str]] = None) -> List[DetectionResult]:
        """
        同步执行检测插件
        :param context: 检测上下文
        :param plugin_names: 指定要执行的插件名称列表，None表示执行所有插件
        :return: 检测结果列表
        """
        plugins_to_run = self._get_plugins_to_run(plugin_names)
        results = []

        for plugin in plugins_to_run:
            if plugin.enabled:
                try:
                    result = plugin.detect(context)
                    if result:
                        results.append(result)
                except Exception as e:
                    # 记录插件执行错误，但不影响其他插件执行
                    import logging
                    logging.error(f"Plugin {plugin.name} execution failed: {str(e)}")

        return results

    async def run_async(self, context: DetectionContext, plugin_names: Optional[List[str]] = None) -> List[DetectionResult]:
        """
        异步执行检测插件（并行执行）
        :param context: 检测上下文
        :param plugin_names: 指定要执行的插件名称列表，None表示执行所有插件
        :return: 检测结果列表
        """
        plugins_to_run = self._get_plugins_to_run(plugin_names)
        tasks = []

        for plugin in plugins_to_run:
            if plugin.enabled:
                task = self._run_plugin_async(plugin, context)
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 过滤掉异常和None结果
        valid_results = []
        for result in results:
            if isinstance(result, DetectionResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                import logging
                logging.error(f"Plugin execution failed: {str(result)}")

        return valid_results

    def _get_plugins_to_run(self, plugin_names: Optional[List[str]] = None) -> List[BaseDetectionPlugin]:
        """
        获取需要执行的插件列表
        :param plugin_names: 指定的插件名称列表
        :return: 插件实例列表
        """
        if plugin_names is None:
            return list(self.plugins.values())

        plugins = []
        for name in plugin_names:
            plugin = self.plugins.get(name)
            if plugin:
                plugins.append(plugin)
        return plugins

    async def _run_plugin_async(self, plugin: BaseDetectionPlugin, context: DetectionContext) -> Optional[DetectionResult]:
        """
        异步执行单个插件
        :param plugin: 插件实例
        :param context: 检测上下文
        :return: 检测结果
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self.executor, plugin.detect, context)
        except Exception as e:
            import logging
            logging.error(f"Plugin {plugin.name} async execution failed: {str(e)}")
            return None

    def shutdown(self) -> None:
        """关闭调度器，释放资源"""
        self.executor.shutdown(wait=True)
```
