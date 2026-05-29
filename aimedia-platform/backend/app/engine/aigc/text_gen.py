"""AIGC 文本生成 —— 科普文章、标题优化、摘要提取"""

from app.llm.gateway import llm_gateway, TaskType


async def generate_article(topic: str, specialty: str = "", target_audience: str = "普通公众",
                           word_count: int = 800) -> str:
    prompt = f"""你是{specialty or '医学'}领域的健康科普作家。请撰写一篇面向{target_audience}的科普文章。

主题: {topic}
字数: 约{word_count}字
要求:
- 语言通俗易懂，避免过多专业术语
- 如有专业术语必须解释
- 不涉及任何医疗广告、疗效承诺
- 不推介任何具体医疗机构或药品
- 文末注明"本文为健康科普内容，不能替代专业医疗建议" """

    result = await llm_gateway.chat(prompt, task_type=TaskType.COMPLEX)
    return result.content


async def optimize_title(body: str, style: str = "科普风") -> list[str]:
    """生成 5 个候选标题"""
    prompt = f"""为以下健康科普文章生成 5 个标题候选。要求:{style}风格，吸引人但不标题党，不超过25字。

文章内容:
{body[:2000]}

输出 JSON 数组:
["标题1", "标题2", "标题3", "标题4", "标题5"]"""

    return await llm_gateway.chat_json(prompt, task_type=TaskType.SIMPLE)


async def extract_summary(body: str, max_length: int = 200) -> str:
    """从长文中提取摘要"""
    prompt = f"""请用不超过{max_length}字总结以下健康科普文章的核心要点。

{body[:3000]}"""

    result = await llm_gateway.chat(prompt, task_type=TaskType.SIMPLE, max_tokens=max_length)
    return result.content


async def generate_script(topic: str, duration_minutes: int = 3) -> str:
    """生成短视频口播脚本"""
    word_count = duration_minutes * 200
    prompt = f"""你是医疗健康短视频编导。为以下主题写一个{duration_minutes}分钟的口播脚本。

主题: {topic}
要求:
- 开头 3 秒抓住注意力（痛点/悬念/反差）
- 正文分 3 个要点，每点 1 句核心信息 + 1 句解释
- 结尾有明确的 call-to-action（点赞/关注/分享/自测）
- 口语化，适合口播
- 标注 [画面建议] 和 [字幕强调]"""

    result = await llm_gateway.chat(prompt, task_type=TaskType.COMPLEX)
    return result.content
