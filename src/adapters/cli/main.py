import click
import json
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

from agent_security_detector import SecurityDetector
from agent_security_detector.core.context import DetectionResponse

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Agent Security Detector - 智能体安全检测工具"""
    pass

@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True, dir_okay=False),
              help='输入JSON文件路径，包含检测数据。如果不指定，从标准输入读取。')
@click.option('--output', '-o', type=click.Path(dir_okay=False),
              help='输出文件路径。如果不指定，输出到标准输出。')
@click.option('--output-format', '-f', type=click.Choice(['json', 'text', 'csv']),
              default='text', help='输出格式。默认: text')
@click.option('--rule-dir', '-r', type=click.Path(exists=True, file_okay=False),
              multiple=True, help='规则目录路径，可以指定多个。')
@click.option('--plugin', '-p', multiple=True, help='指定要运行的插件名称，可以指定多个。')
@click.option('--min-confidence', '-c', type=float, default=0.5,
              help='最低置信度阈值。默认: 0.5')
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息。')
def detect(
    input: Optional[str],
    output: Optional[str],
    output_format: str,
    rule_dir: List[str],
    plugin: List[str],
    min_confidence: float,
    verbose: bool
):
    """执行安全检测"""
    try:
        # 读取输入数据
        if input:
            with open(input, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
        else:
            input_data = json.load(sys.stdin)

        # 初始化检测器
        detector = SecurityDetector(
            config={
                "min_confidence": min_confidence
            },
            rule_dirs=list(rule_dir)
        )

        # 执行检测
        result = detector.detect(
            prompt=input_data.get("prompt", ""),
            response=input_data.get("response", ""),
            tool_calls=input_data.get("tool_calls", []),
            conversation_history=input_data.get("conversation_history", []),
            session_id=input_data.get("session_id"),
            user_id=input_data.get("user_id"),
            agent_id=input_data.get("agent_id"),
            plugin_names=list(plugin) if plugin else None
        )

        # 输出结果
        output_content = _format_output(result, output_format, verbose)

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(output_content)
        else:
            click.echo(output_content)

        # 如果有风险，返回非零退出码
        if result.has_risk:
            sys.exit(1)

    except Exception as e:
        click.echo(f"检测失败: {str(e)}", err=True)
        sys.exit(2)
    finally:
        if 'detector' in locals():
            detector.shutdown()

def _format_output(result: DetectionResponse, output_format: str, verbose: bool) -> str:
    """格式化输出结果"""
    if output_format == "json":
        return result.model_dump_json(indent=2, ensure_ascii=False)

    elif output_format == "csv":
        lines = ["风险等级,风险类型,描述,置信度,插件名称"]
        for risk in result.results:
            line = f"{risk.risk_level},{risk.risk_type},{risk.description},{risk.confidence},{risk.plugin_name}"
            lines.append(line)
        return "\n".join(lines)

    else:  # text format
        lines = []
        lines.append(f"检测结果: {'存在风险' if result.has_risk else '无风险'}")
        lines.append(f"会话ID: {result.session_id or '-'}")
        lines.append(f"最高风险等级: {result.highest_risk_level.value if result.highest_risk_level else '-'}")
        lines.append(f"处理时间: {result.processing_time:.2f}ms")

        if result.results:
            lines.append("\n检测到的风险:")
            for i, risk in enumerate(result.results, 1):
                lines.append(f"\n{i}. [{risk.risk_level.value}] {risk.risk_type}")
                lines.append(f"   描述: {risk.description}")
                lines.append(f"   置信度: {risk.confidence:.2f}")
                lines.append(f"   检测插件: {risk.plugin_name}")
                if risk.suggestion:
                    lines.append(f"   建议: {risk.suggestion}")
                if verbose and risk.details:
                    lines.append(f"   详细信息: {json.dumps(risk.details, ensure_ascii=False, indent=6)}")

        return "\n".join(lines)

if __name__ == "__main__":
    cli()
```
