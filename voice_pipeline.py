
# -*- coding: utf-8 -*-
"""语音处理管线：方言→数字→后处理→模板匹配"""
import re

class VoicePipeline:
    def __init__(self, dialect_map, digit_rules, post_rules):
        self.dialect_map = {d["方言"] if isinstance(d["方言"], str) else d["方言"][0]: d["标准"] for d in dialect_map}
        self.post_rules = post_rules
        self.digit_patterns = [(re.compile(r["模式"]), r["替换"]) for r in digit_rules if "模式" in r]
        self.voice_digit = {"零":"0","一":"1","二":"2","三":"3","四":"4","五":"5","六":"6","七":"7","八":"8","九":"9"}

    def clean(self, text):
        """完整管线"""
        # Step 1: 删除思考填充词
        text = re.sub(r'(嗯[。， ]|让我看看|我想想|这个[，.]|那个[，.]|看一哈|等一哈)', '', text)
        # Step 2: 删除与患者对话
        text = re.sub(r'(放松[。， ]|不要[。， ]|别动[。， ]|忍一下|好了好了|不要要紧|和患者说[：:].*)', '', text)
        # Step 3: 删除交叉对话(打字员/助手行)
        text = re.sub(r'(打字员|助手|护士)[：:].*\n?', '', text)
        # Step 4: 口误修正 - 取最后值
        text = re.sub(r'.*?(不对不对|说错了|不是|改一下|等一下)[，。\s]*', '', text)
        # Step 5: 中文数字转换
        for pattern, repl in self.digit_patterns:
            text = pattern.sub(repl, text)
        # Step 6: 方言映射
        for dialect, standard in self.dialect_map.items():
            text = text.replace(dialect, standard)
        # Step 7: 标准化数字格式
        text = re.sub(r'点(\d)', r'.\1', text)
        return text.strip()

    def process(self, raw_text):
        cleaned = self.clean(raw_text)
        return {
            "input": raw_text,
            "normalized": cleaned,
            "can_route": bool(cleaned and len(cleaned) > 2)
        }

# 使用示例
if __name__ == "__main__":
    pipe = VoicePipeline(DIALECT_MAP, DIGIT_RULES, POST_RULES)
    cases = [
        "右乳外上点八乘零点五低回声",
        "胆囊头头有个一点二的石头",
        "腰子左叶有个水泡泡，边界清",
        "嗯，右乳外上...不对不对，零点九乘零点六",
        "放松点不要紧张，右乳外上零点八低回声",
    ]
    for c in cases:
        r = pipe.process(c)
        print(f"  IN:  {r['input']}")
        print(f"  OUT: {r['normalized']}")
        print()
