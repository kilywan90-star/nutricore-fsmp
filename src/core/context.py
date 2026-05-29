from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DetectionContext(BaseModel):
    """检测上下文，包含所有需要检测的信息"""
    # 基本输入输出
    prompt: str = Field(description="用户输入prompt")
    response: str = Field(description="智能体输出响应")

    # 智能体内部状态
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="工具调用记录")
    internal_state: Dict[str, Any] = Field(default_factory=dict, description="智能体内部状态")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="对话历史")

    # 元信息
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    agent_id: Optional[str] = Field(None, description="智能体ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="检测时间戳")

    # 扩展字段
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

class DetectionResult(BaseModel):
    """检测结果"""
    plugin_name: str = Field(description="检测插件名称")
    risk_level: RiskLevel = Field(description="风险等级")
    risk_type: str = Field(description="风险类型")
    description: str = Field(description="风险描述")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    suggestion: Optional[str] = Field(None, description="处理建议")
    timestamp: datetime = Field(default_factory=datetime.now, description="检测时间")

class DetectionResponse(BaseModel):
    """统一的检测响应"""
    session_id: Optional[str] = Field(None, description="会话ID")
    has_risk: bool = Field(default=False, description="是否存在风险")
    highest_risk_level: Optional[RiskLevel] = Field(None, description="最高风险等级")
    results: List[DetectionResult] = Field(default_factory=list, description="所有检测结果")
    processing_time: float = Field(description="处理时间(ms)")
```
