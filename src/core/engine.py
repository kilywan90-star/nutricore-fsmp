import time
from typing import Any, Dict, List, Optional

from agent_security_detector.core.context import DetectionContext, DetectionResponse
from agent_security_detector.core.scheduler import PluginScheduler
from agent_security_detector.core.aggregator import ResultAggregator
from agent_security_detector.rule_manager.rule_loader import RuleLoader

class SecurityDetector:
    """安全检测引擎，对外的主要接口"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        rule_dirs: Optional[List[str]] = None,
        auto_load_builtin_plugins: bool = True
    ):
        """
        初始化安全检测器
        :param config: 全局配置
        :param rule_dirs: 规则目录列表
        :param auto_load_builtin_plugins: 是否自动加载内置插件
        """
        self.config = config or {}
        self.rule_dirs = rule_dirs or []

        # 初始化核心组件
        self.scheduler = PluginScheduler(
            max_workers=self.config.get("max_workers", 10)
        )
        self.aggregator = ResultAggregator(
            min_confidence=self.config.get("min_confidence", 0.5),
            duplicate_dedup=self.config.get("duplicate_dedup", True)
        )
        self.rule_loader = RuleLoader()

        # 加载内置插件和规则
        if auto_load_builtin_plugins:
            self._load_builtin_plugins()
        if self.rule_dirs:
            self._load_rules()

    def detect(
        self,
        prompt: str,
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        plugin_names: Optional[List[str]] = None
    ) -> DetectionResponse:
        """
        执行安全检测（同步接口）
        :param prompt: 用户输入
        :param response: 智能体输出
        :param tool_calls: 工具调用记录
        :param conversation_history: 对话历史
        :param session_id: 会话ID
        :param user_id: 用户ID
        :param agent_id: 智能体ID
        :param metadata: 扩展元数据
        :param plugin_names: 指定要执行的插件列表
        :return: 检测结果
        """
        start_time = time.time()

        # 构造检测上下文
        context = DetectionContext(
            prompt=prompt,
            response=response,
            tool_calls=tool_calls or [],
            conversation_history=conversation_history or [],
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            metadata=metadata or {}
        )

        # 执行检测
        results = self.scheduler.run_sync(context, plugin_names)

        # 聚合结果
        return self.aggregator.aggregate(results, session_id, start_time)

    async def detect_async(
        self,
        prompt: str,
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        plugin_names: Optional[List[str]] = None
    ) -> DetectionResponse:
        """
        执行安全检测（异步接口）
        :param prompt: 用户输入
        :param response: 智能体输出
        :param tool_calls: 工具调用记录
        :param conversation_history: 对话历史
        :param session_id: 会话ID
        :param user_id: 用户ID
        :param agent_id: 智能体ID
        :param metadata: 扩展元数据
        :param plugin_names: 指定要执行的插件列表
        :return: 检测结果
        """
        start_time = time.time()

        # 构造检测上下文
        context = DetectionContext(
            prompt=prompt,
            response=response,
            tool_calls=tool_calls or [],
            conversation_history=conversation_history or [],
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            metadata=metadata or {}
        )

        # 执行检测
        results = await self.scheduler.run_async(context, plugin_names)

        # 聚合结果
        return self.aggregator.aggregate(results, session_id, start_time)

    def register_plugin(self, plugin: Any) -> None:
        """
        注册自定义插件
        :param plugin: 检测插件实例
        """
        self.scheduler.register_plugin(plugin)

    def load_rules_from_dir(self, rule_dir: str) -> None:
        """
        从目录加载规则
        :param rule_dir: 规则目录路径
        """
        self.rule_loader.load_from_dir(rule_dir)
        # 重新加载插件配置
        self._reload_plugin_configs()

    def _load_builtin_plugins(self) -> None:
        """加载内置检测插件"""
        try:
            # 导入并注册内置插件
            from agent_security_detector.plugins.content_safety.sensitive_info import SensitiveInfoPlugin
            from agent_security_detector.plugins.tool_call_safety.injection_detection import InjectionDetectionPlugin
            from agent_security_detector.plugins.adversarial_detection.prompt_injection import PromptInjectionPlugin

            self.scheduler.register_plugin(SensitiveInfoPlugin({}))
            self.scheduler.register_plugin(InjectionDetectionPlugin({}))
            self.scheduler.register_plugin(PromptInjectionPlugin({}))
        except ImportError:
            # 插件还未实现时忽略
            pass

    def _load_rules(self) -> None:
        """加载规则"""
        for rule_dir in self.rule_dirs:
            self.rule_loader.load_from_dir(rule_dir)
        self._reload_plugin_configs()

    def _reload_plugin_configs(self) -> None:
        """重新加载插件配置"""
        # 根据加载的规则更新插件配置
        rules = self.rule_loader.get_all_rules()
        for plugin_name, plugin in self.scheduler.plugins.items():
            if plugin_name in rules:
                plugin.config.update(rules[plugin_name])

    def shutdown(self) -> None:
        """关闭检测器，释放资源"""
        self.scheduler.shutdown()
```
